"""
Structural Vision Monitor — Offline Analysis Pipeline
======================================================
Processes a pre-recorded video to extract vibration displacement,
dominant frequencies, and damping ratio.

Usage
-----
    python main.py [--video PATH] [--cutoff HZ] [--scale MM_PER_PIXEL]
                   [--start FRAME] [--end FRAME] [--method log_decrement|envelope]

Output
------
    results/
        displacement.png   — filtered displacement time-series
        fft.png            — FFT frequency spectrum
        psd.png            — Welch PSD (more reliable for short signals)
        report.txt         — summary of key metrics
"""

import os
import argparse
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from feature_tracker import VibrationTracker
from motion_compensation import compensate_motion
from signal_analysis import (
    smooth_signal,
    compute_fft,
    compute_welch_psd,
    highpass_filter,
    bandpass_filter,
    dominant_frequency,
    top_n_frequencies,
    estimate_damping,
    signal_snr,
    rms_displacement,
)
from calibration import pixel_to_mm
from utils import save_plot


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Structural Vibration Analysis")
    p.add_argument("--video",   default="data/test_video.mp4")
    p.add_argument("--cutoff",  type=float, default=1.0,  help="High-pass cutoff Hz")
    p.add_argument("--scale",   type=float, default=1.0,  help="mm per pixel")
    p.add_argument("--start",   type=int,   default=None, help="Damping segment start frame")
    p.add_argument("--end",     type=int,   default=None, help="Damping segment end frame")
    p.add_argument("--method",  default="log_decrement",  help="Damping method")
    p.add_argument("--results", default="results")
    return p.parse_args()


# --------------------------------------------------------------------------
# Plotting helpers
# --------------------------------------------------------------------------

def plot_displacement(signal, fps, results_dir, title="Filtered Displacement Signal"):
    t = np.arange(len(signal)) / fps
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(t, signal, linewidth=0.8, color="#1f77b4")
    ax.set_title(title, fontsize=13)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Displacement (mm)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = os.path.join(results_dir, "displacement.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_fft(freqs, mags, dom_freq, dom_mag, results_dir, max_hz=25):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(freqs, mags, linewidth=0.9, color="#1f77b4", label="FFT magnitude")
    ax.scatter([dom_freq], [dom_mag], color="red", zorder=5,
               label=f"Peak: {dom_freq:.2f} Hz")
    ax.set_title("Frequency Spectrum (FFT)", fontsize=13)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Magnitude")
    ax.set_xlim(0, max_hz)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = os.path.join(results_dir, "fft.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_psd(freqs, psd, results_dir, max_hz=25):
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.semilogy(freqs, psd, linewidth=0.9, color="#ff7f0e")
    ax.set_title("Power Spectral Density (Welch)", fontsize=13)
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("PSD")
    ax.set_xlim(0, max_hz)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    path = os.path.join(results_dir, "psd.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {path}")


def plot_overview(t, signal, freqs, mags, psd_f, psd, dom_freq, dom_mag, results_dir):
    """4-panel summary figure."""
    fig = plt.figure(figsize=(14, 8))
    gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.45, wspace=0.35)

    ax1 = fig.add_subplot(gs[0, :])
    ax1.plot(t, signal, linewidth=0.7)
    ax1.set_title("Filtered Displacement (Time Domain)")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Displacement (mm)")
    ax1.grid(True, alpha=0.3)

    ax2 = fig.add_subplot(gs[1, 0])
    ax2.plot(freqs, mags, linewidth=0.8)
    ax2.scatter([dom_freq], [dom_mag], color="red", zorder=5, label=f"{dom_freq:.2f} Hz")
    ax2.set_title("FFT Spectrum")
    ax2.set_xlabel("Frequency (Hz)")
    ax2.set_ylabel("Magnitude")
    ax2.set_xlim(0, 25)
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    ax3 = fig.add_subplot(gs[1, 1])
    ax3.semilogy(psd_f, psd, linewidth=0.8, color="orange")
    ax3.set_title("Welch PSD")
    ax3.set_xlabel("Frequency (Hz)")
    ax3.set_ylabel("PSD")
    ax3.set_xlim(0, 25)
    ax3.grid(True, alpha=0.3)

    fig.suptitle("Structural Vibration Monitor — Summary", fontsize=14, y=1.01)
    path = os.path.join(results_dir, "overview.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {path}")


# --------------------------------------------------------------------------
# Main pipeline
# --------------------------------------------------------------------------

def main():
    args = parse_args()
    results_dir = args.results
    os.makedirs(results_dir, exist_ok=True)

    print("\n=== Structural Vision Monitor ===\n")

    # --- 1. Track features ---
    print("[1/6] Tracking features...")
    tracker = VibrationTracker(args.video)
    displacements, fps = tracker.run()
    print(f"      Video: {len(displacements)} frames @ {fps:.1f} fps")

    # --- 2. Aggregate to scalar signal ---
    print("[2/6] Aggregating displacement signal...")
    raw_signal = compensate_motion(displacements, axis="y")

    # --- 3. Filter ---
    print("[3/6] Filtering (high-pass)...")
    smoothed = smooth_signal(raw_signal, window=5)
    filtered = highpass_filter(smoothed, fps, cutoff=args.cutoff)

    # --- 4. Calibrate ---
    print("[4/6] Calibrating to physical units...")
    physical_signal = pixel_to_mm(filtered, args.scale)

    # --- 5. Frequency analysis ---
    print("[5/6] Frequency analysis...")
    freqs_fft, mags_fft = compute_fft(physical_signal, fps)
    dom_freq, dom_mag = dominant_frequency(freqs_fft, mags_fft)
    top_freqs = top_n_frequencies(freqs_fft, mags_fft, n=5)

    freqs_psd, psd = compute_welch_psd(physical_signal, fps)
    dom_freq_psd, _ = dominant_frequency(freqs_psd, psd)

    snr = signal_snr(physical_signal)
    rms = rms_displacement(physical_signal)

    # --- 6. Damping estimation ---
    print("[6/6] Damping estimation...")
    # Auto-detect ringing segment or use user-specified
    start_f = args.start
    end_f   = args.end

    # Fallback: find the frame with max absolute amplitude as ringing start
    if start_f is None:
        peak_frame = int(np.argmax(np.abs(physical_signal)))
        start_f = max(0, peak_frame)
        end_f   = min(len(physical_signal), peak_frame + int(fps * 3))  # 3s window

    ringing = physical_signal[start_f:end_f]
    damping = estimate_damping(ringing, fps=fps, method=args.method)

    # --- Print summary ---
    t = np.arange(len(physical_signal)) / fps

    print("\n─── Results ───────────────────────────────")
    print(f"  Dominant frequency (FFT)  : {dom_freq:.3f} Hz")
    print(f"  Dominant frequency (Welch): {dom_freq_psd:.3f} Hz")
    print(f"  Top 5 spectral peaks      : {[(round(f,2), round(m,4)) for f,m in top_freqs]}")
    print(f"  Damping ratio (ζ)         : {damping:.4f}" if damping else "  Damping ratio (ζ)         : N/A")
    print(f"  RMS displacement          : {rms:.4f} mm")
    print(f"  Estimated SNR             : {snr:.1f} dB")
    print(f"  Analysis window           : frames {start_f}–{end_f}")
    print("─────────────────────────────────────────\n")

    # --- Plots ---
    print("Saving plots...")
    plot_displacement(physical_signal, fps, results_dir)
    plot_fft(freqs_fft, mags_fft, dom_freq, dom_mag, results_dir)
    plot_psd(freqs_psd, psd, results_dir)
    plot_overview(t, physical_signal, freqs_fft, mags_fft, freqs_psd, psd,
                  dom_freq, dom_mag, results_dir)

    # --- Text report ---
    report_path = os.path.join(results_dir, "report.txt")
    with open(report_path, "w") as f:
        f.write("Structural Vibration Monitor — Analysis Report\n")
        f.write("=" * 50 + "\n\n")
        f.write(f"Video              : {args.video}\n")
        f.write(f"Frames             : {len(displacements)}\n")
        f.write(f"FPS                : {fps:.2f}\n")
        f.write(f"Scale factor       : {args.scale} mm/px\n")
        f.write(f"High-pass cutoff   : {args.cutoff} Hz\n\n")
        f.write(f"Dominant freq (FFT)  : {dom_freq:.3f} Hz\n")
        f.write(f"Dominant freq (Welch): {dom_freq_psd:.3f} Hz\n")
        f.write(f"Top spectral peaks   : {top_freqs}\n")
        f.write(f"Damping ratio (zeta) : {damping:.4f}\n" if damping else "Damping ratio : N/A\n")
        f.write(f"RMS displacement     : {rms:.4f} mm\n")
        f.write(f"SNR estimate         : {snr:.1f} dB\n")
    print(f"  Saved: {report_path}")

    print("\n✓ Processing complete. Results saved to:", results_dir)


if __name__ == "__main__":
    main()
