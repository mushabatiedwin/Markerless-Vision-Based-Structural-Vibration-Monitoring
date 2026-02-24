import numpy as np
from scipy.fft import fft, fftfreq
from scipy.signal import butter, filtfilt

def highpass_filter(signal, fps, cutoff=1.0):
    b, a = butter(2, cutoff / (0.5 * fps), btype='high')
    return filtfilt(b, a, signal)

def smooth_signal(signal, window=7):
    return np.convolve(signal, np.ones(window)/window, mode='same')

def compute_fft(signal, fps):
    N = len(signal)
    yf = fft(signal)
    xf = fftfreq(N, 1/fps)

    positive = xf > 0
    return xf[positive], np.abs(yf[positive])

def dominant_frequency(frequencies, magnitudes):
    idx = np.argmax(magnitudes)
    return frequencies[idx], magnitudes[idx]