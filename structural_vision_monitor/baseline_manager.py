"""
Baseline Management and Deviation Tracking
==========================================
Stores reference measurements and detects deviations from baseline
for condition monitoring and damage detection.
"""

import json
import os
import numpy as np
from datetime import datetime
from typing import Dict, Optional, Tuple


class BaselineManager:
    """Manages baseline storage and deviation analysis."""

    def __init__(self, baseline_dir="baselines"):
        """
        Parameters
        ----------
        baseline_dir : str
            Directory where baseline files are stored.
        """
        self.baseline_dir = baseline_dir
        os.makedirs(baseline_dir, exist_ok=True)
        self.current_baseline = None

    def create_baseline(self, metrics: Dict, name: str = "default"):
        """
        Save current metrics as a baseline reference.

        Parameters
        ----------
        metrics : dict
            Contains keys: frequency, damping, rms, snr, spectral_peaks, timestamp
        name : str
            Baseline identifier.

        Returns
        -------
        bool
            True if baseline saved successfully.
        """
        baseline = {
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "frequency": float(metrics.get("frequency", 0.0)),
                "damping": float(metrics.get("damping", 0.0)),
                "rms": float(metrics.get("rms", 0.0)),
                "snr": float(metrics.get("snr", 0.0)),
                "spectral_peaks": metrics.get("spectral_peaks", []),
            }
        }

        path = os.path.join(self.baseline_dir, f"{name}.json")
        try:
            with open(path, "w") as f:
                json.dump(baseline, f, indent=2)
            self.current_baseline = baseline
            return True
        except Exception as e:
            print(f"[BaselineManager] Error saving baseline: {e}")
            return False

    def load_baseline(self, name: str = "default") -> Optional[Dict]:
        """
        Load a previously saved baseline.

        Parameters
        ----------
        name : str
            Baseline identifier.

        Returns
        -------
        dict or None
        """
        path = os.path.join(self.baseline_dir, f"{name}.json")
        if not os.path.exists(path):
            return None

        try:
            with open(path, "r") as f:
                baseline = json.load(f)
            self.current_baseline = baseline
            return baseline
        except Exception as e:
            print(f"[BaselineManager] Error loading baseline: {e}")
            return None

    def list_baselines(self) -> list:
        """Return list of available baseline names."""
        try:
            files = [f[:-5] for f in os.listdir(self.baseline_dir) if f.endswith(".json")]
            return sorted(files)
        except Exception:
            return []

    def compare_to_baseline(
        self,
        current_metrics: Dict,
        baseline_name: str = "default"
    ) -> Dict:
        """
        Compare current metrics against a baseline.

        Parameters
        ----------
        current_metrics : dict
            Contains: frequency, damping, rms, snr, spectral_peaks
        baseline_name : str
            Which baseline to compare against.

        Returns
        -------
        dict with keys:
            - deviations: {metric: percent_change}
            - severity: 'normal' | 'warning' | 'critical'
            - max_deviation: float (largest percent change)
            - alerts: list of alert messages
        """
        baseline = self.load_baseline(baseline_name)
        if baseline is None:
            return {
                "deviations": {},
                "severity": "unknown",
                "max_deviation": 0.0,
                "alerts": [f"Baseline '{baseline_name}' not found"]
            }

        baseline_metrics = baseline["metrics"]
        current = current_metrics

        deviations = {}
        alerts = []

        # Compare frequency (tolerance: ±5%)
        freq_dev = self._percent_change(
            baseline_metrics["frequency"],
            current.get("frequency", 0.0)
        )
        deviations["frequency"] = freq_dev
        if abs(freq_dev) > 15:
            alerts.append(f"Frequency shift: {freq_dev:+.1f}%")

        # Compare damping (tolerance: ±20%)
        damp_dev = self._percent_change(
            baseline_metrics["damping"],
            current.get("damping", 0.0)
        )
        deviations["damping"] = damp_dev
        if abs(damp_dev) > 30:
            alerts.append(f"Damping change: {damp_dev:+.1f}%")

        # Compare RMS displacement (tolerance: ±10%)
        rms_dev = self._percent_change(
            baseline_metrics["rms"],
            current.get("rms", 0.0)
        )
        deviations["rms"] = rms_dev
        if abs(rms_dev) > 25:
            alerts.append(f"Amplitude change: {rms_dev:+.1f}%")

        # SNR trend (should stay stable or improve)
        snr_dev = self._percent_change(
            baseline_metrics["snr"],
            current.get("snr", 0.0)
        )
        deviations["snr"] = snr_dev
        if snr_dev < -10:
            alerts.append("Signal quality degraded (SNR down)")

        max_dev = max(abs(v) for v in deviations.values()) if deviations else 0.0

        # Severity classification
        if max_dev > 40 or len(alerts) >= 3:
            severity = "critical"
        elif max_dev > 20 or len(alerts) >= 2:
            severity = "warning"
        else:
            severity = "normal"

        return {
            "deviations": deviations,
            "severity": severity,
            "max_deviation": float(max_dev),
            "alerts": alerts
        }

    @staticmethod
    def _percent_change(baseline_val: float, current_val: float) -> float:
        """Calculate percent change from baseline to current."""
        if baseline_val == 0:
            return 0.0 if current_val == 0 else 100.0
        return float(100.0 * (current_val - baseline_val) / abs(baseline_val))

    def reset_baseline(self, name: str = "default") -> bool:
        """Delete a baseline file."""
        path = os.path.join(self.baseline_dir, f"{name}.json")
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except Exception:
            return False
