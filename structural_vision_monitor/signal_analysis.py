import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import butter, filtfilt, find_peaks, welch


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

def highpass_filter(signal, fps, cutoff=1.0, order=4):
    """Zero-phase Butterworth high-pass filter."""
    nyq = 0.5 * fps
    if cutoff >= nyq:
        raise ValueError(f"Cutoff {cutoff} Hz >= Nyquist {nyq} Hz")
    b, a = butter(order, cutoff / nyq, btype="high")
    return filtfilt(b, a, signal)


def lowpass_filter(signal, fps, cutoff=20.0, order=4):
    """Zero-phase Butterworth low-pass filter."""
    nyq = 0.5 * fps
    if cutoff >= nyq:
        raise ValueError(f"Cutoff {cutoff} Hz >= Nyquist {nyq} Hz")
    b, a = butter(order, cutoff / nyq, btype="low")
    return filtfilt(b, a, signal)


def bandpass_filter(signal, fps, low=1.0, high=20.0, order=4):
    """Zero-phase Butterworth band-pass filter."""
    nyq = 0.5 * fps
    b, a = butter(order, [low / nyq, high / nyq], btype="band")
    return filtfilt(b, a, signal)


def smooth_signal(signal, window=7):
    """Simple moving-average smoother."""
    kernel = np.ones(window) / window
    return np.convolve(signal, kernel, mode="same")


# ---------------------------------------------------------------------------
# Frequency domain
# ---------------------------------------------------------------------------

def compute_fft(signal, fps):
    """
    Single-sided FFT.

    Returns
    -------
    frequencies : np.ndarray  positive frequencies only
    magnitudes  : np.ndarray  corresponding magnitudes (not normalized)
    """
    N = len(signal)
    yf = fft(signal - np.mean(signal))   # remove DC bias before FFT
    xf = fftfreq(N, 1.0 / fps)
    pos = xf > 0
    return xf[pos], np.abs(yf[pos]) * 2 / N


def compute_welch_psd(signal, fps, nperseg=None):
    """
    Power Spectral Density via Welch's method — much more reliable than
    a plain FFT for short, noisy signals.

    Returns frequencies and PSD in (units)^2 / Hz.
    """
    if nperseg is None:
        nperseg = min(len(signal) // 4, 256)
    f, psd = welch(signal - np.mean(signal), fs=fps, nperseg=nperseg)
    return f, psd


def dominant_frequency(frequencies, magnitudes, min_hz=0.5):
    """Return (frequency, magnitude) of the highest peak above min_hz."""
    mask = frequencies >= min_hz
    if not np.any(mask):
        return 0.0, 0.0
    idx = np.argmax(magnitudes[mask])
    freqs_valid = frequencies[mask]
    mags_valid = magnitudes[mask]
    return float(freqs_valid[idx]), float(mags_valid[idx])


def top_n_frequencies(frequencies, magnitudes, n=5, min_hz=0.5, min_prominence=0.05):
    """
    Return the top-N distinct spectral peaks ranked by magnitude.

    Parameters
    ----------
    min_prominence : float
        Fraction of max magnitude — filters trivial bumps.

    Returns
    -------
    list of (freq_hz, magnitude) tuples sorted by magnitude descending.
    """
    mask = frequencies >= min_hz
    f = frequencies[mask]
    m = magnitudes[mask]

    peak_indices, props = find_peaks(m, prominence=min_prominence * np.max(m))
    if len(peak_indices) == 0:
        return []

    ranked = sorted(zip(f[peak_indices], m[peak_indices]), key=lambda x: -x[1])
    return ranked[:n]


# ---------------------------------------------------------------------------
# Damping estimation
# ---------------------------------------------------------------------------

def estimate_damping(signal, fps=None, method="log_decrement"):
    """
    Estimate viscous damping ratio ζ from a free-decay segment.

    Parameters
    ----------
    signal : array-like
        Free-decay portion of the displacement signal.
    fps    : float or None
        Required when method='envelope'.
    method : str
        'log_decrement' — classic successive-peak method (fast, simple).
        'envelope'      — Hilbert envelope fitting (more robust, needs fps).

    Returns
    -------
    zeta : float or None
    """
    signal = np.asarray(signal, dtype=np.float64)

    if method == "log_decrement":
        return _damping_log_decrement(signal)
    elif method == "envelope":
        return _damping_envelope(signal, fps)
    else:
        raise ValueError(f"Unknown method: {method}")


def _damping_log_decrement(signal):
    """
    Logarithmic decrement from successive positive peaks.
    Uses median log-ratio over all consecutive peak pairs for robustness.
    """
    peaks_idx, _ = find_peaks(signal, prominence=0.01 * np.max(np.abs(signal)))

    if len(peaks_idx) < 2:
        return None

    peak_amps = signal[peaks_idx]
    # Filter out non-positive peaks (needed for log)
    pos_mask = peak_amps > 0
    peaks_idx = peaks_idx[pos_mask]
    peak_amps = peak_amps[pos_mask]

    if len(peak_amps) < 2:
        return None

    ratios = peak_amps[:-1] / peak_amps[1:]
    ratios = ratios[ratios > 0]

    if len(ratios) == 0:
        return None

    delta = np.median(np.log(ratios))
    zeta = delta / np.sqrt(4 * np.pi ** 2 + delta ** 2)
    return float(np.clip(zeta, 0.0, 1.0))


def _damping_envelope(signal, fps):
    """Hilbert transform envelope decay fit — more robust for noisy signals."""
    from scipy.signal import hilbert
    from scipy.optimize import curve_fit

    analytic = hilbert(signal)
    envelope = np.abs(analytic)

    t = np.arange(len(signal)) / fps

    def exponential_decay(t, A, zeta_wd):
        return A * np.exp(-zeta_wd * t)

    try:
        popt, _ = curve_fit(exponential_decay, t, envelope, p0=[envelope[0], 1.0], maxfev=5000)
        decay_rate = popt[1]          # = ζ * ω_n
        # We can't recover ζ without ω_n here, so return decay rate directly
        # Caller should divide by (2π * fn) if fn is known
        return float(decay_rate)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Signal quality metrics
# ---------------------------------------------------------------------------

def signal_snr(signal):
    """
    Estimate SNR as ratio of AC power to noise floor power.
    Uses the top 10% of FFT as signal, bottom 50% as noise floor estimate.
    """
    mag = np.abs(fft(signal - np.mean(signal)))
    mag_sorted = np.sort(mag)[::-1]
    n = len(mag_sorted)
    signal_power = np.mean(mag_sorted[: max(1, n // 10)] ** 2)
    noise_power = np.mean(mag_sorted[n // 2 :] ** 2)
    if noise_power < 1e-12:
        return float("inf")
    return float(10 * np.log10(signal_power / noise_power))


def rms_displacement(signal):
    """Root-mean-square displacement amplitude."""
    return float(np.sqrt(np.mean(signal ** 2)))
