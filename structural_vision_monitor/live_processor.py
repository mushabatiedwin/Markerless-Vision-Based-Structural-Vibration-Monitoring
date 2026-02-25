"""
Live Processor — Real-time webcam vibration analysis
======================================================
Captures frames, tracks features, and computes vibration metrics
in a background thread. Exposes thread-safe getters for the API.
"""

import threading
import time
import cv2
import numpy as np

from signal_analysis import (
    compute_welch_psd,
    compute_fft,
    dominant_frequency,
    estimate_damping,
    highpass_filter,
    rms_displacement,
)

# ---------------------------------------------------------------------------
# Shared state (protected by _lock)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_latest_metrics = {
    "frequency": 0.0,
    "damping": 0.0,
    "rms": 0.0,
    "status": "Initializing",
    "signal_buffer": [],   # last N samples for live chart
}

_latest_frame = None          # annotated BGR frame
_signal_buffer = []           # raw pixel-displacement history
_running = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FPS = 30
BUFFER_SIZE = 300             # ~10 s at 30 fps
ANALYSIS_WINDOW = 150         # frames used for FFT / damping
REINIT_EVERY = 90             # re-detect features every N frames

FEATURE_PARAMS = dict(maxCorners=200, qualityLevel=0.01, minDistance=7, blockSize=7)
LK_PARAMS = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.03),
)


# ---------------------------------------------------------------------------
# Background processing thread
# ---------------------------------------------------------------------------

def start_processing(camera_index=0):
    global _running
    if _running:
        return
    _running = True
    t = threading.Thread(target=_processing_loop, args=(camera_index,), daemon=True)
    t.start()


def _processing_loop(camera_index):
    global _latest_frame, _signal_buffer, _latest_metrics

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        with _lock:
            _latest_metrics["status"] = "Camera error"
        return

    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    fps = actual_fps if actual_fps > 5 else FPS

    ret, first_frame = cap.read()
    if not ret:
        with _lock:
            _latest_metrics["status"] = "Camera read error"
        return

    prev_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
    prev_pts = cv2.goodFeaturesToTrack(prev_gray, mask=None, **FEATURE_PARAMS)

    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        frame_idx += 1
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # --- Optical flow ---
        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, gray, prev_pts, None, **LK_PARAMS
        )

        annotated = frame.copy()

        if next_pts is not None and np.sum(status) >= 4:
            good_new = next_pts[status.ravel() == 1]
            good_old = prev_pts[status.ravel() == 1]

            # Homography camera compensation
            displacement_y = _get_structural_displacement(good_old, good_new)

            with _lock:
                _signal_buffer.append(displacement_y)
                if len(_signal_buffer) > BUFFER_SIZE:
                    _signal_buffer.pop(0)

            # Draw tracked points
            for pt in good_new.reshape(-1, 2):
                cv2.circle(annotated, tuple(pt.astype(int).tolist()), 2, (0, 255, 0), -1)

            prev_gray = gray.copy()
            prev_pts = good_new.reshape(-1, 1, 2)
        else:
            # Re-initialize
            prev_pts = cv2.goodFeaturesToTrack(gray, mask=None, **FEATURE_PARAMS)
            prev_gray = gray.copy()

        # Periodic re-init
        if frame_idx % REINIT_EVERY == 0:
            prev_pts = cv2.goodFeaturesToTrack(gray, mask=None, **FEATURE_PARAMS)

        # --- Overlay metrics on frame ---
        with _lock:
            m = _latest_metrics.copy()

        status_color = {
            "Stable": (0, 200, 0),
            "Moderate Vibration": (0, 165, 255),
            "High Vibration": (0, 0, 255),
        }.get(m["status"], (200, 200, 200))

        cv2.putText(annotated, f"Freq: {m['frequency']:.2f} Hz",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(annotated, f"Damp: {m['damping']:.4f}",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.putText(annotated, m["status"],
                    (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)

        with _lock:
            _latest_frame = annotated

        # --- Analysis (every ~1 s) ---
        if frame_idx % int(fps) == 0:
            _run_analysis(fps)

        time.sleep(max(0, 1.0 / fps - 0.002))

    cap.release()


def _get_structural_displacement(pts_old, pts_new):
    """Homography-compensated vertical displacement (scalar)."""
    if len(pts_old) >= 8:
        H, mask = cv2.findHomography(
            pts_old.reshape(-1, 1, 2),
            pts_new.reshape(-1, 1, 2),
            cv2.RANSAC, 3.0
        )
        if H is not None:
            predicted = cv2.perspectiveTransform(pts_old.reshape(-1, 1, 2).astype(np.float32), H)
            structural = pts_new - predicted.reshape(-1, 2)
            return float(np.median(structural[:, 1]))

    # Fallback: median subtraction
    dy = pts_new[:, 1] - pts_old[:, 1]
    return float(np.median(dy) - np.median(dy))   # = 0 when no structure motion


def _run_analysis(fps):
    global _latest_metrics

    with _lock:
        buf = list(_signal_buffer)

    if len(buf) < ANALYSIS_WINDOW:
        return

    signal = np.array(buf[-ANALYSIS_WINDOW:], dtype=np.float64)

    try:
        # High-pass to remove slow drift
        from signal_analysis import highpass_filter
        signal = highpass_filter(signal, fps, cutoff=0.5)
    except Exception:
        pass

    # Welch PSD (more reliable than raw FFT for live data)
    try:
        f_psd, psd = compute_welch_psd(signal, fps)
        dom_freq_psd, _ = dominant_frequency(f_psd, psd, min_hz=0.3)
    except Exception:
        dom_freq_psd = 0.0

    # Damping
    damping = estimate_damping(signal, fps=fps, method="log_decrement")

    # RMS
    rms = rms_displacement(signal)

    # Status label
    if dom_freq_psd < 2:
        status_label = "Stable"
    elif dom_freq_psd < 8:
        status_label = "Moderate Vibration"
    else:
        status_label = "High Vibration"

    with _lock:
        _latest_metrics = {
            "frequency": round(float(dom_freq_psd), 2),
            "damping": round(float(damping), 4) if damping else 0.0,
            "rms": round(float(rms), 4),
            "status": status_label,
            "signal_buffer": signal[-60:].tolist(),   # last 60 pts for live chart
        }


# ---------------------------------------------------------------------------
# Public getters (thread-safe)
# ---------------------------------------------------------------------------

def get_latest_metrics():
    with _lock:
        return dict(_latest_metrics)


def get_latest_frame():
    with _lock:
        return _latest_frame
