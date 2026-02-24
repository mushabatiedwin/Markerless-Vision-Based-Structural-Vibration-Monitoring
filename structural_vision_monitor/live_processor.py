import cv2
import numpy as np
import time
from signal_analysis import compute_fft, estimate_damping

latest_metrics = {
    "frequency": 0,
    "damping": 0,
    "status": "Initializing"
}

latest_frame = None
signal_buffer = []
fps = 30

feature_params = dict(
    maxCorners=200,
    qualityLevel=0.01,
    minDistance=7,
    blockSize=7
)

lk_params = dict(
    winSize=(21, 21),
    maxLevel=3,
    criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 20, 0.03)
)

def start_processing():
    global latest_metrics, latest_frame

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)  # Use DirectShow backend (fix MSMF issue)

    ret, first_frame = cap.read()
    if not ret:
        print("Camera failed to start.")
        return

    prev_gray = cv2.cvtColor(first_frame, cv2.COLOR_BGR2GRAY)
    prev_pts = cv2.goodFeaturesToTrack(prev_gray, mask=None, **feature_params)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        latest_frame = frame.copy()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            prev_gray, gray, prev_pts, None, **lk_params
        )

        if next_pts is None:
            continue

        good_new = next_pts[status == 1]
        good_old = prev_pts[status == 1]

        if len(good_new) == 0:
            continue

        displacement = np.mean((good_new - good_old)[:, 1])
        signal_buffer.append(displacement)

        prev_gray = gray.copy()
        prev_pts = good_new.reshape(-1, 1, 2)

        if len(signal_buffer) > 200:
            signal = np.array(signal_buffer[-200:])
            freqs, mags = compute_fft(signal, fps)

            dominant_freq = freqs[np.argmax(mags)]
            damping = estimate_damping(signal[-150:])

            if dominant_freq < 3:
                status_label = "Stable"
            elif dominant_freq < 8:
                status_label = "Moderate Vibration"
            else:
                status_label = "High Vibration"

            latest_metrics = {
                "frequency": round(float(dominant_freq), 2),
                "damping": round(float(damping), 4) if damping else 0,
                "status": status_label
            }

        time.sleep(1 / fps)

def get_latest_metrics():
    return latest_metrics

def get_latest_frame():
    return latest_frame
