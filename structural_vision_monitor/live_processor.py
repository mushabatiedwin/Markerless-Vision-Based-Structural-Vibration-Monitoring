import cv2
import numpy as np
import time
from signal_analysis import compute_fft, estimate_damping

latest_metrics = {
    "frequency": 0,
    "damping": 0,
    "status": "Initializing"
}

signal_buffer = []
fps = 30

def start_processing():
    global latest_metrics
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # SIMPLE displacement proxy (mean intensity change)
        displacement = np.mean(gray)
        signal_buffer.append(displacement)

        if len(signal_buffer) > 300:
            signal = np.array(signal_buffer[-300:])
            freqs, mags = compute_fft(signal, fps)

            dominant_freq = freqs[np.argmax(mags)]
            damping = estimate_damping(signal[-200:])

            # AI Health Logic
            if dominant_freq < 3:
                status = "Stable"
            elif dominant_freq < 8:
                status = "Moderate Vibration"
            else:
                status = "High Vibration"

            latest_metrics = {
                "frequency": round(float(dominant_freq), 2),
                "damping": round(float(damping), 4),
                "status": status
            }

        time.sleep(1 / fps)

def get_latest_metrics():
    return latest_metrics