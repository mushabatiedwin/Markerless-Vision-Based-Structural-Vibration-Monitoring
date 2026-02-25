"""
Event Detection — Impact and Anomaly Monitoring
===============================================
Detects sudden impacts, impulses, and anomalous behavior in real-time.
"""

import numpy as np
from scipy.signal import find_peaks
from datetime import datetime
from typing import List, Dict, Tuple


class EventDetector:
    """Detects impacts and anomalous events in displacement signals."""

    def __init__(self, fps: float = 30.0, detection_window: int = 150):
        """
        Parameters
        ----------
        fps : float
            Sampling rate in frames per second.
        detection_window : int
            Number of samples to analyze for event detection.
        """
        self.fps = fps
        self.detection_window = detection_window
        self.event_history = []

    def detect_impact(self, signal: np.ndarray) -> Dict:
        """
        Detect sharp impacts (high-frequency, short-duration peaks).

        Parameters
        ----------
        signal : np.ndarray
            Displacement signal (last N samples).

        Returns
        -------
        dict with keys:
            - detected: bool
            - peak_magnitude: float
            - peak_time: float (seconds from start)
            - rise_time: float (seconds to peak)
            - severity: 'low' | 'medium' | 'high'
        """
        signal = np.asarray(signal, dtype=np.float64)
        if len(signal) < 10:
            return {
                "detected": False,
                "peak_magnitude": 0.0,
                "peak_time": 0.0,
                "rise_time": 0.0,
                "severity": "none"
            }

        # Normalize for peak detection
        abs_signal = np.abs(signal)
        threshold = np.median(abs_signal) + 2.0 * np.std(abs_signal)

        peaks, props = find_peaks(
            abs_signal,
            height=threshold,
            distance=int(self.fps / 10)  # peaks at least 100ms apart
        )

        if len(peaks) == 0:
            return {
                "detected": False,
                "peak_magnitude": 0.0,
                "peak_time": 0.0,
                "rise_time": 0.0,
                "severity": "none"
            }

        # Most recent peak
        peak_idx = peaks[-1]
        peak_mag = float(abs_signal[peak_idx])
        peak_time = float(peak_idx / self.fps)

        # Estimate rise time (from 10% to peak)
        peak_height = peak_mag * 0.1
        rise_start = peak_idx
        for i in range(peak_idx - 1, -1, -1):
            if abs_signal[i] < peak_height:
                rise_start = i
                break
        rise_time = float((peak_idx - rise_start) / self.fps)

        # Severity based on magnitude relative to median
        median_amp = np.median(abs_signal)
        if median_amp == 0:
            severity = "low"
        else:
            ratio = peak_mag / median_amp
            if ratio > 5.0:
                severity = "high"
            elif ratio > 2.5:
                severity = "medium"
            else:
                severity = "low"

        event = {
            "detected": True,
            "peak_magnitude": peak_mag,
            "peak_time": peak_time,
            "rise_time": rise_time,
            "severity": severity,
            "timestamp": datetime.now().isoformat()
        }

        self.event_history.append(event)
        return event

    def detect_resonance_excitation(self, freqs: np.ndarray, psd: np.ndarray) -> Dict:
        """
        Detect sudden excitation of resonant modes (narrow spectral peaks).

        Parameters
        ----------
        freqs : np.ndarray
            Frequency array from PSD.
        psd : np.ndarray
            Power spectral density.

        Returns
        -------
        dict with keys:
            - detected: bool
            - peak_frequency: float
            - q_factor: float (sharpness of peak)
            - power_increase: float (dB)
        """
        if len(freqs) < 5 or len(psd) < 5:
            return {
                "detected": False,
                "peak_frequency": 0.0,
                "q_factor": 0.0,
                "power_increase": 0.0
            }

        # Find peaks in PSD
        psd_db = 10 * np.log10(np.maximum(psd, 1e-12))
        peaks, props = find_peaks(psd_db, prominence=3.0)

        if len(peaks) == 0:
            return {
                "detected": False,
                "peak_frequency": 0.0,
                "q_factor": 0.0,
                "power_increase": 0.0
            }

        # Highest peak
        peak_idx = peaks[np.argmax(props["prominences"])]
        peak_freq = float(freqs[peak_idx])
        prominence = float(props["prominences"][peaks == peak_idx][0])

        # Q factor: sharpness of resonance (-3dB bandwidth method)
        peak_height = psd_db[peak_idx]
        half_height = peak_height - 3.0

        left_idx = peak_idx
        for i in range(peak_idx - 1, -1, -1):
            if psd_db[i] < half_height:
                left_idx = i
                break

        right_idx = peak_idx
        for i in range(peak_idx + 1, len(psd_db)):
            if psd_db[i] < half_height:
                right_idx = i
                break

        bw = freqs[right_idx] - freqs[left_idx] if right_idx > left_idx else 1.0
        q_factor = float(peak_freq / max(bw, 0.1))

        detected = prominence > 5.0 and q_factor > 3.0

        return {
            "detected": detected,
            "peak_frequency": peak_freq,
            "q_factor": q_factor,
            "power_increase": prominence
        }

    def detect_anomaly(self, signal: np.ndarray, baseline_stats: Dict) -> Dict:
        """
        Detect statistical anomalies (outliers, bursts, etc.).

        Parameters
        ----------
        signal : np.ndarray
            Displacement signal.
        baseline_stats : dict
            Contains: mean, std, max_expected

        Returns
        -------
        dict with keys:
            - anomaly_detected: bool
            - anomaly_type: 'burst' | 'outlier' | 'trend' | 'none'
            - severity: float (0-1)
            - details: str
        """
        signal = np.asarray(signal, dtype=np.float64)
        if len(signal) < 10:
            return {
                "anomaly_detected": False,
                "anomaly_type": "none",
                "severity": 0.0,
                "details": ""
            }

        mean = baseline_stats.get("mean", np.mean(signal))
        std = baseline_stats.get("std", np.std(signal))
        max_expected = baseline_stats.get("max_expected", mean + 4 * std)

        # Check for outliers (> 3 sigma)
        outlier_mask = np.abs(signal - mean) > 3.5 * std
        outlier_ratio = np.sum(outlier_mask) / len(signal)

        if outlier_ratio > 0.05:  # > 5% outliers
            return {
                "anomaly_detected": True,
                "anomaly_type": "outlier",
                "severity": float(min(outlier_ratio, 1.0)),
                "details": f"{outlier_ratio*100:.1f}% of samples are outliers"
            }

        # Check for burst (short high-amplitude segment)
        window_size = int(self.fps * 0.5)  # 500ms window
        if len(signal) >= window_size:
            rms_windows = []
            for i in range(0, len(signal) - window_size + 1):
                rms = np.sqrt(np.mean(signal[i:i+window_size] ** 2))
                rms_windows.append(rms)

            rms_windows = np.array(rms_windows)
            if len(rms_windows) > 0:
                max_rms = np.max(rms_windows)
                mean_rms = np.mean(rms_windows)

                if max_rms > 2.5 * mean_rms:
                    burst_severity = min((max_rms - mean_rms) / (3 * mean_rms), 1.0)
                    return {
                        "anomaly_detected": True,
                        "anomaly_type": "burst",
                        "severity": float(burst_severity),
                        "details": f"Energy burst: {max_rms:.2f} vs {mean_rms:.2f} mean RMS"
                    }

        # Check for trend (drift)
        if len(signal) >= 20:
            first_half = np.mean(signal[:len(signal)//2])
            second_half = np.mean(signal[len(signal)//2:])
            drift = abs(second_half - first_half) / (std + 1e-9)

            if drift > 2.0:
                return {
                    "anomaly_detected": True,
                    "anomaly_type": "trend",
                    "severity": min(drift / 5.0, 1.0),
                    "details": f"Increasing trend detected: {first_half:.2f} → {second_half:.2f}"
                }

        return {
            "anomaly_detected": False,
            "anomaly_type": "none",
            "severity": 0.0,
            "details": ""
        }

    def get_event_summary(self, lookback_seconds: float = 60.0) -> Dict:
        """
        Get summary of recent events.

        Parameters
        ----------
        lookback_seconds : float
            How far back to look in event history.

        Returns
        -------
        dict with event counts and recent impacts
        """
        recent_events = []
        now = datetime.now()

        for evt in self.event_history:
            try:
                evt_time = datetime.fromisoformat(evt["timestamp"])
                elapsed = (now - evt_time).total_seconds()
                if elapsed < lookback_seconds:
                    recent_events.append(evt)
            except Exception:
                pass

        high_severity = sum(1 for e in recent_events if e.get("severity") == "high")
        medium_severity = sum(1 for e in recent_events if e.get("severity") == "medium")

        return {
            "total_events": len(self.event_history),
            "recent_events": len(recent_events),
            "high_severity": high_severity,
            "medium_severity": medium_severity,
            "latest_event": recent_events[-1] if recent_events else None
        }
