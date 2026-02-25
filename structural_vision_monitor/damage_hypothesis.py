"""
Damage Hypothesis Detection
===========================
Detects signatures that may indicate structural cracks or damage
based on signal characteristics and frequency changes.
"""

import numpy as np
from typing import Dict, List, Tuple


class DamageHypothesis:
    """Detects potential cracks and damage based on structural signatures."""

    def __init__(self):
        self.previous_state = {}

    def assess_damage_likelihood(
        self,
        current_metrics: Dict,
        baseline_metrics: Dict = None,
        signal: np.ndarray = None
    ) -> Dict:
        """
        Comprehensive damage assessment based on multiple indicators.

        Parameters
        ----------
        current_metrics : dict
            Contains: frequency, damping, rms, snr, spectral_peaks
        baseline_metrics : dict, optional
            Reference metrics for comparison.
        signal : np.ndarray, optional
            Raw displacement signal for detailed analysis.

        Returns
        -------
        dict with keys:
            - crack_likelihood: float (0-1, probability of crack)
            - damage_indicator: float (0-1, overall damage indicator)
            - damage_type: str ('none' | 'surface_crack' | 'deep_crack' | 'fracture' | 'unknown')
            - indicators: dict of individual damage signatures
            - warning_level: str ('none' | 'caution' | 'alert' | 'critical')
            - recommendations: list of strings
        """
        indicators = {}

        # ─── Indicator 1: Frequency shift (stiffness loss) ─────────────────
        freq_indicator = self._check_frequency_shift(current_metrics, baseline_metrics)
        indicators["frequency_shift"] = freq_indicator

        # ─── Indicator 2: Damping increase (energy dissipation) ────────────
        damp_indicator = self._check_damping_increase(current_metrics, baseline_metrics)
        indicators["damping_increase"] = damp_indicator

        # ─── Indicator 3: Broadening spectral peaks (loss of coherence) ────
        peak_indicator = self._check_spectral_broadening(current_metrics, baseline_metrics)
        indicators["spectral_broadening"] = peak_indicator

        # ─── Indicator 4: Signal quality degradation ───────────────────────
        snr_indicator = self._check_signal_quality(current_metrics, baseline_metrics)
        indicators["signal_degradation"] = snr_indicator

        # ─── Indicator 5: Non-stationary behavior (material scatter) ───────
        if signal is not None:
            scatter_indicator = self._check_material_scatter(signal)
            indicators["material_scatter"] = scatter_indicator
        else:
            scatter_indicator = {"score": 0.0, "details": "No signal data"}
            indicators["material_scatter"] = scatter_indicator

        # ─── Indicator 6: High-frequency content increase ──────────────────
        hf_indicator = self._check_high_frequency_content(current_metrics, baseline_metrics)
        indicators["high_frequency_content"] = hf_indicator

        # Aggregate indicators
        scores = [ind.get("score", 0.0) for ind in indicators.values()]
        damage_indicator = float(np.mean(scores)) if scores else 0.0
        crack_likelihood = float(np.clip(damage_indicator, 0.0, 1.0))

        # Classify damage type
        damage_type = self._classify_damage_type(indicators)

        # Determine warning level
        warning_level = self._classify_warning_level(crack_likelihood, damage_type)

        # Generate recommendations
        recommendations = self._generate_recommendations(damage_type, indicators)

        result = {
            "crack_likelihood": crack_likelihood,
            "damage_indicator": damage_indicator,
            "damage_type": damage_type,
            "indicators": indicators,
            "warning_level": warning_level,
            "recommendations": recommendations
        }

        self.previous_state = result
        return result

    @staticmethod
    def _check_frequency_shift(current_metrics: Dict, baseline_metrics: Dict = None) -> Dict:
        """
        Detect stiffness loss via frequency reduction.
        A 5-10% drop may indicate minor cracks; >15% suggests significant damage.
        """
        if baseline_metrics is None:
            return {"score": 0.0, "details": "No baseline"}

        baseline_freq = baseline_metrics.get("frequency", 0.0)
        current_freq = current_metrics.get("frequency", 0.0)

        if baseline_freq == 0:
            return {"score": 0.0, "details": "Invalid baseline"}

        pct_change = 100.0 * (current_freq - baseline_freq) / baseline_freq

        if pct_change >= -2:  # Within normal variation
            score = 0.0
        elif pct_change >= -10:  # Minor shift
            score = 0.3
        elif pct_change >= -20:  # Moderate shift
            score = 0.6
        else:  # Severe shift
            score = 0.9

        return {
            "score": float(score),
            "pct_change": float(pct_change),
            "details": f"Frequency: {baseline_freq:.2f} → {current_freq:.2f} Hz ({pct_change:+.1f}%)"
        }

    @staticmethod
    def _check_damping_increase(current_metrics: Dict, baseline_metrics: Dict = None) -> Dict:
        """
        Detect increased damping (energy dissipation from micro-cracking).
        Damping typically increases 20-50% with surface cracks.
        """
        if baseline_metrics is None:
            return {"score": 0.0, "details": "No baseline"}

        baseline_damp = baseline_metrics.get("damping", 0.0)
        current_damp = current_metrics.get("damping", 0.0)

        if baseline_damp == 0:
            return {"score": 0.0, "details": "Baseline damping is zero"}

        pct_change = 100.0 * (current_damp - baseline_damp) / abs(baseline_damp)

        if pct_change <= 15:  # Normal
            score = 0.0
        elif pct_change <= 35:  # Mild increase
            score = 0.35
        elif pct_change <= 60:  # Significant increase
            score = 0.65
        else:  # Severe increase
            score = 0.85

        return {
            "score": float(score),
            "pct_change": float(pct_change),
            "details": f"Damping: {baseline_damp:.4f} → {current_damp:.4f} ({pct_change:+.1f}%)"
        }

    @staticmethod
    def _check_spectral_broadening(current_metrics: Dict, baseline_metrics: Dict = None) -> Dict:
        """
        Detect broadening of spectral peaks (loss of coherence, scattering from cracks).
        """
        if baseline_metrics is None:
            return {"score": 0.0, "details": "No baseline"}

        baseline_peaks = baseline_metrics.get("spectral_peaks", [])
        current_peaks = current_metrics.get("spectral_peaks", [])

        if not baseline_peaks or not current_peaks:
            return {"score": 0.0, "details": "Missing spectral peak data"}

        # Compare peak Q-factors (inverse of bandwidth)
        # Lower Q = broader peak = more scatter/damage
        baseline_q = np.mean([p.get("q_factor", 3.0) for p in baseline_peaks[:3]])
        current_q = np.mean([p.get("q_factor", 3.0) for p in current_peaks[:3]])

        if current_q >= baseline_q:  # Peaks are sharper = good
            score = 0.0
        elif current_q >= 0.5 * baseline_q:  # Moderate broadening
            score = 0.4
        elif current_q >= 0.3 * baseline_q:  # Significant broadening
            score = 0.65
        else:  # Severe broadening
            score = 0.85

        return {
            "score": float(score),
            "baseline_q": float(baseline_q),
            "current_q": float(current_q),
            "details": f"Peak Q-factor: {baseline_q:.1f} → {current_q:.1f}"
        }

    @staticmethod
    def _check_signal_quality(current_metrics: Dict, baseline_metrics: Dict = None) -> Dict:
        """Detect SNR degradation (may indicate measurement uncertainty or damage scatter)."""
        if baseline_metrics is None:
            return {"score": 0.0, "details": "No baseline"}

        baseline_snr = baseline_metrics.get("snr", 20.0)
        current_snr = current_metrics.get("snr", 20.0)

        snr_drop = baseline_snr - current_snr

        if snr_drop <= 3:  # Normal
            score = 0.0
        elif snr_drop <= 8:  # Mild degradation
            score = 0.25
        elif snr_drop <= 15:  # Moderate degradation
            score = 0.5
        else:  # Severe degradation
            score = 0.7

        return {
            "score": float(score),
            "snr_drop": float(snr_drop),
            "details": f"SNR: {baseline_snr:.1f} → {current_snr:.1f} dB"
        }

    @staticmethod
    def _check_material_scatter(signal: np.ndarray) -> Dict:
        """
        Detect non-stationary behavior (variance changes over time).
        Cracks cause energy scattering leading to non-stationary signals.
        """
        signal = np.asarray(signal, dtype=np.float64)
        if len(signal) < 20:
            return {"score": 0.0, "details": "Signal too short"}

        # Split signal into quarters and compare variance
        n = len(signal)
        q1 = np.var(signal[:n//4])
        q2 = np.var(signal[n//4:n//2])
        q3 = np.var(signal[n//2:3*n//4])
        q4 = np.var(signal[3*n//4:])

        variances = [q1, q2, q3, q4]
        mean_var = np.mean(variances)
        cv = np.std(variances) / (mean_var + 1e-9)  # Coefficient of variation

        if cv < 0.15:  # Stable
            score = 0.0
        elif cv < 0.35:  # Mild variation
            score = 0.2
        elif cv < 0.60:  # Moderate variation
            score = 0.45
        else:  # High variation
            score = 0.7

        return {
            "score": float(score),
            "cv": float(cv),
            "details": f"Signal non-stationarity: CV = {cv:.3f}"
        }

    @staticmethod
    def _check_high_frequency_content(current_metrics: Dict, baseline_metrics: Dict = None) -> Dict:
        """
        Detect increase in high-frequency content (crack friction noise).
        """
        if baseline_metrics is None:
            return {"score": 0.0, "details": "No baseline"}

        baseline_peaks = baseline_metrics.get("spectral_peaks", [])
        current_peaks = current_metrics.get("spectral_peaks", [])

        if not baseline_peaks or not current_peaks:
            return {"score": 0.0, "details": "No spectral peak data"}

        # Look at mean frequency of peaks
        baseline_mean_freq = np.mean([p.get("frequency", 5.0) for p in baseline_peaks[:3]])
        current_mean_freq = np.mean([p.get("frequency", 5.0) for p in current_peaks[:3]])

        freq_shift = current_mean_freq - baseline_mean_freq

        if freq_shift <= 0.5:  # Stable
            score = 0.0
        elif freq_shift <= 2.0:  # Mild
            score = 0.2
        elif freq_shift <= 5.0:  # Moderate
            score = 0.5
        else:  # Significant shift to higher frequencies
            score = 0.7

        return {
            "score": float(score),
            "freq_shift": float(freq_shift),
            "details": f"Mean peak frequency: {baseline_mean_freq:.1f} → {current_mean_freq:.1f} Hz"
        }

    @staticmethod
    def _classify_damage_type(indicators: Dict) -> str:
        """Classify damage type based on indicator pattern."""
        freq_score = indicators.get("frequency_shift", {}).get("score", 0.0)
        damp_score = indicators.get("damping_increase", {}).get("score", 0.0)
        broad_score = indicators.get("spectral_broadening", {}).get("score", 0.0)
        scatter_score = indicators.get("material_scatter", {}).get("score", 0.0)
        hf_score = indicators.get("high_frequency_content", {}).get("score", 0.0)

        # Signature patterns
        if damp_score > 0.5 and broad_score > 0.5 and scatter_score > 0.4:
            return "deep_crack"
        elif damp_score > 0.4 and broad_score > 0.3 and freq_score > 0.3:
            return "surface_crack"
        elif freq_score > 0.8 and damp_score > 0.6:
            return "fracture"
        elif hf_score > 0.6 and scatter_score > 0.5:
            return "unknown"
        else:
            return "none"

    @staticmethod
    def _classify_warning_level(crack_likelihood: float, damage_type: str) -> str:
        """Determine warning level based on likelihood and type."""
        if damage_type == "none" or crack_likelihood < 0.2:
            return "none"
        elif damage_type == "unknown" or crack_likelihood < 0.4:
            return "caution"
        elif crack_likelihood < 0.65:
            return "alert"
        else:
            return "critical"

    @staticmethod
    def _generate_recommendations(damage_type: str, indicators: Dict) -> List[str]:
        """Generate actionable recommendations based on damage assessment."""
        recommendations = []

        if damage_type == "none":
            recommendations.append("✓ Structure appears healthy. Continue routine monitoring.")
            return recommendations

        if damage_type == "surface_crack":
            recommendations.append("⚠ Possible surface crack detected.")
            recommendations.append("→ Inspect visible surfaces for hairline cracks.")
            recommendations.append("→ Perform ultrasonic testing to assess crack depth.")

        elif damage_type == "deep_crack":
            recommendations.append("🚨 Deep structural crack likely.")
            recommendations.append("→ Schedule urgent structural assessment.")
            recommendations.append("→ Consider load restrictions until inspected.")
            recommendations.append("→ Use advanced NDT (ultrasonic, radiography).")

        elif damage_type == "fracture":
            recommendations.append("🚨🚨 CRITICAL: Possible member fracture detected!")
            recommendations.append("→ STOP operations immediately. Structural failure risk.")
            recommendations.append("→ Evacuate personnel if applicable.")
            recommendations.append("→ Emergency inspection required before resumption.")

        elif damage_type == "unknown":
            recommendations.append("⚠ Anomalous signal characteristics detected.")
            recommendations.append("→ Verify calibration and sensor function.")
            recommendations.append("→ Perform visual inspection.")
            recommendations.append("→ Rule out false positives before maintenance actions.")

        return recommendations
