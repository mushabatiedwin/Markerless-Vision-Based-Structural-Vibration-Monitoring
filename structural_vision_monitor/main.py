import os
import matplotlib.pyplot as plt

from feature_tracker import VibrationTracker
from motion_compensation import compensate_motion
from signal_analysis import smooth_signal, compute_fft, highpass_filter
from calibration import pixel_to_mm
from utils import save_plot
from signal_analysis import dominant_frequency

# ---------------- SETTINGS ----------------
video_path = "data/test_video.mp4"
results_dir = "results"
scale_factor = 1.0  # change later if calibrating

os.makedirs(results_dir, exist_ok=True)

# ---------------- TRACKING ----------------
tracker = VibrationTracker(video_path)
displacements, fps = tracker.run()   # <-- fps defined HERE

# ---------------- COMPENSATION ----------------
corrected_signal = compensate_motion(displacements)

# ---------------- SMOOTHING ----------------
smoothed = smooth_signal(corrected_signal, window=7)   # <-- smoothed defined HERE

# ---------------- HIGH PASS FILTER ----------------
filtered = highpass_filter(smoothed, fps, cutoff=3.0)

# ---------------- CALIBRATION ----------------
physical_signal = pixel_to_mm(filtered, scale_factor)

# ---------------- TIME DOMAIN PLOT ----------------
plt.figure()
plt.plot(physical_signal)
plt.title("Filtered Displacement Signal")
plt.xlabel("Frame")
plt.ylabel("Displacement")
plt.savefig(os.path.join(results_dir, "displacement.png"))
plt.close()



frequencies, magnitudes = compute_fft(physical_signal, fps)
# --- Get dominant frequency ---
dom_freq, dom_mag = dominant_frequency(frequencies, magnitudes)
print(f"Dominant Frequency: {dom_freq:.2f} Hz")


# ---------------- FREQUENCY DOMAIN ----------------
frequencies, magnitudes = compute_fft(physical_signal, fps)

plt.figure()
plt.plot(frequencies, magnitudes)
plt.scatter(dom_freq, dom_mag)  # highlight peak
plt.title("Frequency Spectrum")
plt.xlabel("Frequency (Hz)")
plt.ylabel("Magnitude")
plt.xlim(0, 20)
plt.savefig(os.path.join(results_dir, "fft.png"))
plt.close()

print("Processing complete. Results saved in /results.")