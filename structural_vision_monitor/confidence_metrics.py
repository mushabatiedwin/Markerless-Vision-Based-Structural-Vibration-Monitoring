"""
Confidence Metrics and Uncertainty Quantification
=================================================
Estimates measurement uncertainty and confidence levels for vibration metrics.
"""

import numpy as np
from typing import Dict, Tuple


class ConfidenceMetrics:
    """Quantifies uncertainty and confidence in vibration measurements."""

    def __init__(self, history_length: int = 300):
        """
        Parameters
        ----------
        history_length : int
            Number of samples to maintain for stability analysis.
        """
        self.history_length = history_length
        self.frequency_history = []
        self.damping_history = []
        self.rms_history = []

    def update_history(self, metrics: Dict):
        """Update running history of metrics."""
        self.frequency_history.append(metrics.get("frequency", 0.0))
        self.damping_history.append(metrics.get("damping", 0.0))
        self.rms_history.append(metrics.get("rms", 0.0))

        # Keep within length limit
        if len(self.frequency_history) > self.history_length:
            self.frequency_history.pop(0)
        if len(self.damping_history) > self.history_length:
            self.damping_history.pop(0)
        if len(self.rms_history) > self.history_length:
            self.rms_history.pop(0)

    def estimate_confidence(
        self,
        current_metrics: Dict,
        signal: np.ndarray = None,
        num_features: int = 100
    ) -> Dict:
        """
        Comprehensive confidence assessment.

        Parameters
        ----------
        current_metrics : dict
            Contains: frequency, damping, rms, snr, status
        signal : np.ndarray, optional
            Current displacement signal.
        num_features : int
            Number of tracked features (for robustness).

        Returns
        -------
        dict with keys:
            - overall_confidence: float (0-1, higher = more confident)
            - frequency_confidence: float (0-1)
            - damping_confidence: float (0-1)
            - rms_confidence: float (0-1)
            - tracking_confidence: float (0-1)
            - uncertainty_bounds: dict with lower/upper bounds
            - warnings: list of confidence issues
            - quality_score: str ('excellent' | 'good' | 'fair' | 'poor')
        """
        confidences = {}
        warnings = []

        # ─── Frequency confidence ────────────────────────────────────────
        freq_conf, freq_warn = self._assess_frequency_confidence(current_metrics)
        confidences["frequency"] = freq_conf
        if freq_warn:
            warnings.append(freq_warn)

        # ─── Damping confidence ─────────────────────────────────────────
        damp_conf, damp_warn = self._assess_damping_confidence(current_metrics)
        confidences["damping"] = damp_conf
        if damp_warn:
            warnings.append(damp_warn)

        # ─── RMS confidence ─────────────────────────────────────────────
        rms_conf, rms_warn = self._assess_rms_confidence(current_metrics)
        confidences["rms"] = rms_conf
        if rms_warn:
            warnings.append(rms_warn)

        # ─── Tracking robustness ────────────────────────────────────────
        track_conf, track_warn = self._assess_tracking_confidence(num_features)
        confidences["tracking"] = track_conf
        if track_warn:
            warnings.append(track_warn)

        # ─── Signal stationarity ────────────────────────────────────────
        if signal is not None:
            stat_conf, stat_warn = self._assess_signal_stationarity(signal)
            confidences["stationarity"] = stat_conf
            if stat_warn:
                warnings.append(stat_warn)
        else:
            confidences["stationarity"] = 0.7

        # ─── Compute bounds for key metrics ─────────────────────────────
        uncertainty_bounds = self._estimate_uncertainty_bounds(current_metrics)

        # Overall confidence
        conf_values = list(confidences.values())
        overall = float(np.mean(conf_values)) if conf_values else 0.5

        # Quality classification
        quality_score = self._classify_quality(overall, len(warnings))

        return {
            "overall_confidence": overall,
            "frequency_confidence": confidences.get("frequency", 0.5),
            "damping_confidence": confidences.get("damping", 0.5),
            "rms_confidence": confidences.get("rms", 0.5),
            "tracking_confidence": confidences.get("tracking", 0.5),
            "stationarity_confidence": confidences.get("stationarity", 0.5),
            "uncertainty_bounds": uncertainty_bounds,
            "warnings": warnings,
            "quality_score": quality_score,
            "num_issues": len(warnings)
        }

    def _assess_frequency_confidence(self, metrics: Dict) -> Tuple[float, str]:
        """
        Assess confidence in frequency measurement.
        Relies on stability, SNR, and history consistency.
        """
        snr = metrics.get("snr", 20.0)
        freq = metrics.get("frequency", 0.0)

        # SNR-based confidence
        if snr < 5:
            snr_conf = 0.3
            snr_issue = "Low SNR reduces frequency accuracy"
        elif snr < 10:
            snr_conf = 0.6
            snr_issue = None
        elif snr < 20:
            snr_conf = 0.8
            snr_issue = None
        else:
            snr_conf = 0.95
            snr_issue = None

        # History stability (if available)
        if len(self.frequency_history) >= 10:
            recent = np.array(self.frequency_history[-10:])
            if np.max(recent) > 0:
                freq_cv = np.std(recent) / np.mean(recent)
                if freq_cv < 0.02:
                    history_conf = 0.95
                elif freq_cv < 0.05:
                    history_conf = 0.85
                elif freq_cv < 0.10:
                    history_conf = 0.70
                    snr_issue = "Frequency oscillating (poor stability)"
                else:
                    history_conf = 0.50
                    snr_issue = "Frequency highly unstable"
            else:
                history_conf = 0.5
        else:
            history_conf = 0.7

        overall_conf = float(np.mean([snr_conf, history_conf]))
        return overall_conf, snr_issue

    def _assess_damping_confidence(self, metrics: Dict) -> Tuple[float, str]:
        """
        Assess confidence in damping estimation.
        Damping is harder to estimate reliably than frequency.
        """
        damping = metrics.get("damping", 0.0)
        snr = metrics.get("snr", 20.0)

        # Damping value validity
        if damping <= 0:
            damp_conf = 0.2
            issue = "Damping estimation failed (non-positive)"
        elif damping < 0.01:
            damp_conf = 0.5
            issue = "Damping very low (may be unreliable)"
        elif damping < 0.1:
            damp_conf = 0.85
            issue = None
        elif damping < 0.3:
            damp_conf = 0.80
            issue = None
        else:
            damp_conf = 0.6
            issue = "Damping high (estimate may be unstable)"

        # SNR penalty
        if snr < 10:
            damp_conf *= 0.8
            if not issue:
                issue = "Low SNR reduces damping reliability"

        # History consistency
        if len(self.damping_history) >= 10:
            recent = np.array(self.damping_history[-10:])
            recent = recent[recent > 0]  # Filter out invalid values
            if len(recent) > 2:
                damp_cv = np.std(recent) / np.mean(recent)
                if damp_cv > 0.5:
                    damp_conf *= 0.7
                    if not issue:
                        issue = "Damping highly variable (poor stability)"

        return float(np.clip(damp_conf, 0.0, 1.0)), issue

    def _assess_rms_confidence(self, metrics: Dict) -> Tuple[float, str]:
        """
        Assess confidence in RMS displacement.
        More robust than frequency/damping.
        """
        rms = metrics.get("rms", 0.0)
        snr = metrics.get("snr", 20.0)

        # SNR dominates RMS confidence
        if snr < 3:
            rms_conf = 0.4
            issue = "Very low SNR"
        elif snr < 8:
            rms_conf = 0.65
            issue = "Low SNR"
        elif snr < 15:
            rms_conf = 0.85
            issue = None
        else:
            rms_conf = 0.95
            issue = None

        # History consistency
        if len(self.rms_history) >= 10:
            recent = np.array(self.rms_history[-10:])
            if np.mean(recent) > 0:
                rms_cv = np.std(recent) / np.mean(recent)
                if rms_cv > 0.3:
                    rms_conf *= 0.8
                    if not issue:
                        issue = "RMS oscillating"

        return float(np.clip(rms_conf, 0.0, 1.0)), issue

    @staticmethod
    def _assess_tracking_confidence(num_features: int) -> Tuple[float, str]:
        """
        Assess robustness of feature tracking.
        Fewer features = less robust measurements.
        """
        if num_features < 20:
            conf = 0.4
            issue = f"Only {num_features} features tracked (low robustness)"
        elif num_features < 50:
            conf = 0.65
            issue = None
        elif num_features < 100:
            conf = 0.85
            issue = None
        else:
            conf = 0.95
            issue = None

        return float(conf), issue

    @staticmethod
    def _assess_signal_stationarity(signal: np.ndarray) -> Tuple[float, str]:
        """
        Assess stationarity of displacement signal.
        Highly non-stationary → lower confidence.
        """
        signal = np.asarray(signal, dtype=np.float64)
        if len(signal) < 20:
            return 0.7, None

        # Split into quarters and compare statistics
        n = len(signal)
        q1 = signal[:n//4]
        q2 = signal[n//4:n//2]
        q3 = signal[n//2:3*n//4]
        q4 = signal[3*n//4:]

        means = [np.mean(q) for q in [q1, q2, q3, q4]]
        stds = [np.std(q) for q in [q1, q2, q3, q4]]

        mean_cv = np.std(means) / (np.mean(np.abs(means)) + 1e-9)
        std_cv = np.std(stds) / (np.mean(stds) + 1e-9)

        combined_cv = np.mean([mean_cv, std_cv])

        if combined_cv < 0.10:
            conf = 0.95
            issue = None
        elif combined_cv < 0.20:
            conf = 0.85
            issue = None
        elif combined_cv < 0.35:
            conf = 0.70
            issue = "Signal moderately non-stationary"
        else:
            conf = 0.50
            issue = "Signal highly non-stationary (low confidence)"

        return float(conf), issue

    @staticmethod
    def _estimate_uncertainty_bounds(metrics: Dict) -> Dict:
        """
        Estimate 95% confidence intervals for key metrics.
        Uses SNR and historical variability.
        """
        freq = metrics.get("frequency", 0.0)
        damp = metrics.get("damping", 0.0)
        rms = metrics.get("rms", 0.0)
        snr = metrics.get("snr", 20.0)

        # Uncertainty scales inversely with SNR
        # Use empirical relationships
        snr_factor = max(0.05, 10 ** (-snr / 20))  # Convert dB to linear

        freq_uncertainty = freq * snr_factor * 0.1 if freq > 0 else 0.5
        damp_uncertainty = damp * snr_factor * 0.2 if damp > 0 else 0.01
        rms_uncertainty = rms * snr_factor * 0.15 if rms > 0 else 0.1

        return {
            "frequency": {
                "lower": max(0.1, freq - 1.96 * freq_uncertainty),
                "upper": freq + 1.96 * freq_uncertainty,
                "margin": freq_uncertainty
            },
            "damping": {
                "lower": max(0.0, damp - 1.96 * damp_uncertainty),
                "upper": min(1.0, damp + 1.96 * damp_uncertainty),
                "margin": damp_uncertainty
            },
            "rms": {
                "lower": max(0.0, rms - 1.96 * rms_uncertainty),
                "upper": rms + 1.96 * rms_uncertainty,
                "margin": rms_uncertainty
            }
        }

    @staticmethod
    def _classify_quality(overall_conf: float, num_warnings: int) -> str:
        """Classify overall measurement quality."""
        if overall_conf >= 0.90 and num_warnings == 0:
            return "excellent"
        elif overall_conf >= 0.75 and num_warnings <= 1:
            return "good"
        elif overall_conf >= 0.60 and num_warnings <= 2:
            return "fair"
        else:
            return "poor"
