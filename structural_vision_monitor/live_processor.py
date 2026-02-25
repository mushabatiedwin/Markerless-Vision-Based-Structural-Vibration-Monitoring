"""
Enhanced Live Processor — Real-time structural vibration analysis
==================================================================
Integrates baseline comparison, event detection, damage hypothesis,
and confidence metrics into the real-time analysis pipeline.
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
    extract_spectral_peaks,
    signal_snr,
)
from baseline_manager import BaselineManager
from event_detector import EventDetector
from damage_hypothesis import DamageHypothesis
from confidence_metrics import ConfidenceMetrics

# ---------------------------------------------------------------------------
# Shared state (protected by _lock)
# ---------------------------------------------------------------------------

_lock = threading.Lock()

_latest_metrics = {
    "frequency": 0.0,
    "damping": 0.0,
    "rms": 0.0,
    "snr": 0.0,
    "status": "Initializing",
    "signal_buffer": [],
    # New fields for advanced features
    "spectral_peaks": [],
    "baseline_comparison": None,
    "event_detection": None,
    "damage_assessment": None,
    "confidence_metrics": None,
}

_latest_frame = None
_signal_buffer = []
_running = False

# Managers
_baseline_mgr = BaselineManager()
_event_detector = EventDetector()
_damage_assessor = DamageHypothesis()
_confidence_estimator = ConfidenceMetrics()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

FPS = 30
BUFFER_SIZE = 300
ANALYSIS_WINDOW = 150
REINIT_EVERY = 90

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
            prev_pts = cv2.goodFeaturesToTrack(gray, mask=None, **FEATURE_PARAMS)
            prev_gray = gray.copy()

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

        # Add confidence indicator
        if m.get("confidence_metrics"):
            conf = m["confidence_metrics"].get("overall_confidence", 0.5)
            conf_color = (0, 255, 0) if conf > 0.7 else (0, 165, 255) if conf > 0.5 else (0, 0, 255)
            cv2.putText(annotated, f"Conf: {conf:.2f}",
                        (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, conf_color, 2)

        # Add damage flag
        if m.get("damage_assessment"):
            damage_type = m["damage_assessment"].get("damage_type", "none")
            if damage_type != "none":
                damage_color = (0, 0, 255)
                cv2.putText(annotated, f"⚠ {damage_type.upper()}",
                            (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.6, damage_color, 2)

        with _lock:
            _latest_frame = annotated

        # --- Periodic analysis (every ~1 s) ---
        if frame_idx % int(fps) == 0:
            _run_analysis(fps, len(good_new) if next_pts is not None else 0)

        time.sleep(max(0, 1.0 / fps - 0.002))

    cap.release()


def _get_structural_displacement(pts_old, pts_new):
    """Homography-compensated vertical displacement."""
    pts_old = pts_old.reshape(-1, 2).astype(np.float32)
    pts_new = pts_new.reshape(-1, 2).astype(np.float32)

    if len(pts_old) >= 8:
        H, mask = cv2.findHomography(
            pts_old.reshape(-1, 1, 2),
            pts_new.reshape(-1, 1, 2),
            cv2.RANSAC, 3.0
        )
        if H is not None:
            predicted = cv2.perspectiveTransform(
                pts_old.reshape(-1, 1, 2), H
            )
            structural = pts_new - predicted.reshape(-1, 2)
            return float(np.median(structural[:, 1]))

    dy = pts_new[:, 1] - pts_old[:, 1]
    global_dy = np.median(dy)
    return float(np.median(dy - global_dy))


def _run_analysis(fps, num_features):
    global _latest_metrics

    with _lock:
        buf = list(_signal_buffer)

    if len(buf) < ANALYSIS_WINDOW:
        return

    signal = np.array(buf[-ANALYSIS_WINDOW:], dtype=np.float64)

    try:
        signal = highpass_filter(signal, fps, cutoff=0.5)
    except Exception:
        pass

    # ─── 1. Basic metrics ─────────────────────────────────────────────
    try:
        f_psd, psd = compute_welch_psd(signal, fps)
        dom_freq_psd, _ = dominant_frequency(f_psd, psd, min_hz=0.3)
    except Exception:
        dom_freq_psd = 0.0
        f_psd = np.array([])
        psd = np.array([])

    damping = estimate_damping(signal, fps=fps, method="log_decrement")
    rms = rms_displacement(signal)
    snr = signal_snr(signal)

    # Status label
    if dom_freq_psd < 2:
        status_label = "Stable"
    elif dom_freq_psd < 8:
        status_label = "Moderate Vibration"
    else:
        status_label = "High Vibration"

    # ─── 2. Extract spectral peaks ─────────────────────────────────────
    try:
        freqs_fft, mags_fft = compute_fft(signal, fps)
        spectral_peaks = extract_spectral_peaks(freqs_fft, mags_fft, n=5)
    except Exception:
        spectral_peaks = []

    # ─── 3. Baseline comparison ────────────────────────────────────────
    current_metrics = {
        "frequency": dom_freq_psd,
        "damping": damping if damping else 0.0,
        "rms": rms,
        "snr": snr,
        "spectral_peaks": spectral_peaks
    }

    baseline_result = _baseline_mgr.compare_to_baseline(current_metrics)

    # ─── 4. Event detection ────────────────────────────────────────────
    impact_event = _event_detector.detect_impact(signal)
    event_summary = _event_detector.get_event_summary()

    # ─── 5. Damage hypothesis assessment ───────────────────────────────
    baseline_data = _baseline_mgr.load_baseline()
    baseline_metrics = baseline_data["metrics"] if baseline_data else None
    
    damage_result = _damage_assessor.assess_damage_likelihood(
        current_metrics,
        baseline_metrics=baseline_metrics,
        signal=signal
    )

    # ─── 6. Confidence metrics ────────────────────────────────────────
    _confidence_estimator.update_history(current_metrics)
    confidence_result = _confidence_estimator.estimate_confidence(
        current_metrics,
        signal=signal,
        num_features=num_features
    )

    # ─── Update shared state ───────────────────────────────────────────
    with _lock:
        _latest_metrics = {
            "frequency": round(float(dom_freq_psd), 2),
            "damping": round(float(damping), 4) if damping else 0.0,
            "rms": round(float(rms), 4),
            "snr": round(float(snr), 2),
            "status": status_label,
            "signal_buffer": signal[-60:].tolist(),
            "spectral_peaks": spectral_peaks,
            "baseline_comparison": baseline_result,
            "event_detection": {
                "impact": impact_event,
                "event_summary": event_summary
            },
            "damage_assessment": damage_result,
            "confidence_metrics": confidence_result,
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


# ---------------------------------------------------------------------------
# Baseline management API
# ---------------------------------------------------------------------------

def create_baseline(name="default"):
    """Save current metrics as baseline."""
    metrics = get_latest_metrics()
    return _baseline_mgr.create_baseline(metrics, name=name)


def load_baseline(name="default"):
    """Load a saved baseline."""
    return _baseline_mgr.load_baseline(name)


def list_baselines():
    """Get list of available baselines."""
    return _baseline_mgr.list_baselines()


def reset_baseline(name="default"):
    """Delete a baseline."""
    return _baseline_mgr.reset_baseline(name)
