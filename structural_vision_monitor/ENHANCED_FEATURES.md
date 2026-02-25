# Structural Vision Monitor — Enhanced Edition

## Overview

This is an advanced structural health monitoring system with four new capabilities:

1. **Crack/Damage Hypothesis Flag** — Detect structural damage signatures
2. **Baseline Comparison + Deviation Tracking** — Compare current state to reference
3. **Event Detection (Impact Monitoring)** — Detect sudden impacts and anomalies
4. **Uncertainty/Confidence Indicator** — Quantify measurement reliability

---

## Installation & Setup

### Requirements
```bash
pip install numpy opencv-python scipy fastapi uvicorn matplotlib
```

### File Structure
```
/structural_vision_monitor
    api.py                          ← Enhanced FastAPI server
    live_processor.py               ← Real-time pipeline with new features
    signal_analysis.py              ← Updated with spectral peak extraction
    baseline_manager.py             ← NEW: Baseline storage & comparison
    event_detector.py               ← NEW: Impact & anomaly detection
    damage_hypothesis.py            ← NEW: Damage assessment engine
    confidence_metrics.py           ← NEW: Uncertainty quantification
    feature_tracker.py
    motion_compensation.py
    calibration.py
    utils.py
    main.py
    /templates
        index.html                  ← Enhanced dashboard
    /static
        style.css                   ← Enhanced styles
    /baselines                      ← Baseline data storage (auto-created)
    /data
        test_video.mp4
    /results
```

### Running the System

**Start the API server:**
```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

**Access the dashboard:**
Open `http://localhost:8000` in your browser.

---

## Feature Details

### 1. Crack/Damage Hypothesis Flag

Detects structural damage through multi-indicator analysis:

#### Indicators
- **Frequency Shift** — Loss of stiffness (freq reduction 5-20%)
- **Damping Increase** — Energy dissipation from micro-cracking (20-60% rise)
- **Spectral Broadening** — Loss of coherence, scattering from cracks
- **Signal Degradation** — SNR decline indicating measurement uncertainty
- **Material Scatter** — Non-stationary signal behavior (time-varying stats)
- **High-Frequency Content** — Crack friction noise (frequency shift upward)

#### Damage Classification
```
NONE            → No damage indicators
SURFACE_CRACK   → Minor surface crack (caution level)
DEEP_CRACK      → Structural crack reaching deeper layers (alert)
FRACTURE        → Critical member fracture risk (critical)
UNKNOWN         → Anomalous signals, needs further investigation
```

#### API Endpoint
```
GET /damage_assessment
```

Returns:
```json
{
  "crack_likelihood": 0.35,           // 0-1 probability of crack
  "damage_indicator": 0.38,           // overall damage score
  "damage_type": "surface_crack",
  "warning_level": "caution",
  "indicators": {
    "frequency_shift": {...},
    "damping_increase": {...},
    "spectral_broadening": {...},
    ...
  },
  "recommendations": [
    "Inspect visible surfaces...",
    "Perform ultrasonic testing..."
  ]
}
```

---

### 2. Baseline Comparison + Deviation Tracking

Store reference measurements and track deviations from normal state.

#### Key Metrics Tracked
- **Frequency** (tolerance: ±15%)
- **Damping** (tolerance: ±30%)
- **RMS Displacement** (tolerance: ±25%)
- **Signal-to-Noise Ratio** (should stay stable/improve)

#### Severity Levels
```
NORMAL      → All metrics within tolerance
WARNING     → 1-2 metrics exceed thresholds (>20% deviation)
CRITICAL    → Multiple alerts or >40% max deviation
```

#### API Endpoints

**List all baselines:**
```
GET /baselines
Response: {"baselines": ["default", "baseline_14_30", ...]}
```

**Create new baseline (save current state):**
```
POST /baselines/{name}
Response: {"success": true, "message": "Baseline 'safe_state' created"}
```

**Get baseline data:**
```
GET /baselines/{name}
```

**Compare against baseline:**
```
GET /baseline_comparison?baseline=default
Response: {
  "deviations": {
    "frequency": 12.5,              // % change from baseline
    "damping": -8.2,
    "rms": 18.3,
    "snr": -5.1
  },
  "severity": "warning",
  "max_deviation": 18.3,
  "alerts": [
    "Frequency shift: +12.5%",
    "Amplitude change: +18.3%"
  ]
}
```

**Delete baseline:**
```
DELETE /baselines/{name}
```

#### Dashboard Usage
1. **Create Baseline** — Click "📌 Save Baseline" button to record current healthy state
2. **Select Baseline** — Choose which baseline to compare against
3. **Monitor Deviations** — Real-time percentage changes displayed
4. **Review Alerts** — Green (normal), yellow (warning), red (critical)

---

### 3. Event Detection (Impact Monitoring)

Detects sudden impacts, impulses, and anomalous behavior.

#### Detection Types

**A. Impact Detection**
- Identifies sharp peaks (high amplitude, short duration)
- Measures rise time and peak magnitude
- Classifies severity: low / medium / high
- Maintains event history with timestamps

**B. Resonance Excitation**
- Detects sudden activation of resonant modes
- Measures Q-factor (peak sharpness)
- Flags narrow-band energy surges

**C. Anomaly Detection**
- **Outliers**: >3.5σ from mean (>5% of signal)
- **Bursts**: Sudden energy spikes (RMS >2.5× baseline)
- **Trends**: Signal drift over time
- **Material Scatter**: Non-stationary behavior

#### API Endpoints

**Get recent events summary:**
```
GET /events/recent?lookback_seconds=60
Response: {
  "recent_events": 3,
  "high_severity": 1,
  "medium_severity": 1,
  "latest_event": {
    "detected": true,
    "peak_magnitude": 45.2,
    "severity": "high",
    "timestamp": "2024-02-25T14:32:10.5"
  }
}
```

**Get all event data:**
```
GET /events
```

---

### 4. Uncertainty/Confidence Indicator

Quantifies measurement reliability based on SNR, stability, and tracking robustness.

#### Confidence Components

| Component | Factors |
|-----------|---------|
| **Frequency** | SNR, historical stability (CV <2% = excellent) |
| **Damping** | Validity range (0.01-0.1), SNR penalty, variability |
| **RMS** | Most robust; mainly SNR-dependent |
| **Tracking** | Number of tracked features (>100 = excellent) |
| **Stationarity** | Variance stability across signal quarters |

#### Confidence Bands

**SNR-based uncertainty (95% CI):**
```
Frequency:   ±(SNR_factor × 0.1 × f_Hz)
Damping:     ±(SNR_factor × 0.2 × ζ)
RMS:         ±(SNR_factor × 0.15 × rms)
```

Where `SNR_factor = 10^(-SNR_dB/20)`

#### Quality Classification
```
EXCELLENT   → >90% confidence, 0 warnings
GOOD        → >75% confidence, ≤1 warning
FAIR        → >60% confidence, ≤2 warnings
POOR        → <60% confidence or >2 warnings
```

#### API Endpoint
```
GET /confidence
Response: {
  "overall_confidence": 0.82,
  "frequency_confidence": 0.85,
  "damping_confidence": 0.70,
  "rms_confidence": 0.90,
  "tracking_confidence": 0.95,
  "quality_score": "good",
  "num_warnings": 1,
  "warnings": [
    "Low SNR reduces damping reliability"
  ],
  "uncertainty_bounds": {
    "frequency": {
      "lower": 4.8,
      "upper": 5.2,
      "margin": 0.2
    },
    ...
  }
}
```

#### Dashboard Display
- **Confidence gauge** shows overall measurement confidence (0-100%)
- **Per-metric confidence** on metric cards (e.g., "85% conf")
- **Quality badge** indicates overall data quality
- **Warning list** explains confidence issues

---

## API Summary

### Core Metrics
```
GET /health              Health check
GET /metrics             Current vibration metrics
GET /signal?n=60         Last N displacement samples
GET /video_feed          MJPEG camera stream
GET /spectral_peaks      Top spectral peaks with Q-factors
```

### Baseline Management
```
GET /baselines                                List all baselines
POST /baselines/{name}                        Create baseline
GET /baselines/{name}                         Retrieve baseline
DELETE /baselines/{name}                      Delete baseline
GET /baseline_comparison?baseline=default     Compare current to baseline
```

### Advanced Features
```
GET /damage_assessment      Crack/damage likelihood
GET /events                 Impact detection summary
GET /events/recent          Recent high-severity events
GET /confidence             Measurement confidence & uncertainty
```

### Dashboard
```
GET /dashboard              All dashboard data in one request
GET /                       HTML dashboard UI
```

---

## Configuration

### live_processor.py
```python
FPS = 30                    # Sampling rate
BUFFER_SIZE = 300           # Signal buffer (≈10 s @ 30 fps)
ANALYSIS_WINDOW = 150       # FFT/damping window (≈5 s)
FEATURE_PARAMS = {
    "maxCorners": 200,      # Reduce for faster processing
    "qualityLevel": 0.01,
    "minDistance": 7
}
```

### baseline_manager.py
```python
baseline_dir = "baselines"  # Where baseline files are stored
# Baselines are auto-created in JSON format with timestamp
```

### event_detector.py
```python
fps = 30.0                  # Sampling rate
detection_window = 150      # Samples to analyze per update
# Peaks >2.5σ from baseline considered "medium" severity
# Peaks >5σ considered "high" severity
```

### damage_hypothesis.py
```python
# Auto-calibrated thresholds:
# Frequency shift:  >15% drop = high concern
# Damping:         >60% increase = high concern
# Spectral Q:      >50% broadening = concern
```

### confidence_metrics.py
```python
history_length = 300       # Samples to track for stability
# Confidence bins based on:
#  - SNR (dB) to linear sensitivity
#  - Coefficient of variation across signal windows
#  - Feature tracking robustness
```

---

## Typical Workflow

### Initial Setup
1. **Place camera** on structure to monitor
2. **Calibrate** scale (pixels → mm) if needed
3. **Start monitoring** — dashboard shows live metrics

### Establish Baseline
1. **Wait 1-2 minutes** for analysis to stabilize
2. **Click "📌 Save Baseline"** with structure in healthy state
3. **Name it** (e.g., "healthy_state" or date)
4. **Use as reference** for future monitoring

### Ongoing Monitoring
- **Dashboard updates every 1 second**
- **Confidence indicator** shows data quality
- **Deviation tracking** alerts if metrics shift
- **Event log** captures impacts and anomalies
- **Damage assessment** flags structural concern

### Response to Alerts
```
CONFIDENCE WARNING
  → Check sensor focus/calibration
  → Verify feature visibility
  
BASELINE DEVIATION (CAUTION)
  → Review environmental conditions
  → Note any recent activity
  → Monitor trend
  
DAMAGE ALERT
  → Record screenshot of dashboard
  → Note time and circumstances
  → Schedule visual inspection
  
IMPACT DETECTED
  → Log timestamp and magnitude
  → If repeated: investigate source
  → Consider structural impact if severe
  
CRACK LIKELIHOOD > 50%
  → Escalate to structural engineer
  → Prepare for detailed NDT
  → Consider operational restrictions
```

---

## Example Integration

### Python Script: Auto-Save Baselines
```python
import live_processor
import time

# Start monitoring
live_processor.start_processing(camera_index=0)
time.sleep(120)  # Wait 2 minutes for stabilization

# Save baseline
success = live_processor.create_baseline("startup")
if success:
    print("✓ Baseline saved")

# Monitor for 1 hour
for i in range(3600):
    metrics = live_processor.get_latest_metrics()
    damage = metrics.get("damage_assessment", {})
    
    if damage.get("warning_level") == "critical":
        print(f"🚨 CRITICAL: {damage.get('damage_type')}")
        break
    
    time.sleep(1)
```

### Web Client: Get Damage Status
```javascript
fetch('/damage_assessment')
  .then(r => r.json())
  .then(data => {
    if (data.crack_likelihood > 0.5) {
      console.warn('⚠️ Damage likely:', data.damage_type);
      showAlert(data.recommendations.join('\n'));
    }
  });
```

---

## Troubleshooting

### Confidence Too Low (<0.6)?
- [ ] Check camera focus and lighting
- [ ] Verify >100 features are being tracked
- [ ] Reduce scene motion (vibration is OK, camera motion is bad)
- [ ] Check SNR in metrics (should be >10 dB)

### High False-Positive Damage Alerts?
- [ ] Verify camera is stable (use tripod/clamp)
- [ ] Establish baseline in calm conditions
- [ ] Check for environmental factors (wind, etc.)
- [ ] Review actual damage indicators before taking action

### Baseline Comparison Not Working?
- [ ] Ensure baseline file exists in `/baselines/{name}.json`
- [ ] Check baseline was created successfully
- [ ] Verify metrics are being computed (wait 2 mins after startup)

### Events Not Detected?
- [ ] Check ANALYSIS_WINDOW is enough samples (min ~150)
- [ ] Verify signal has sufficient amplitude
- [ ] Check event_detector is initialized in live_processor
- [ ] Review event severity thresholds

---

## Limitations & Future Work

### Current Limitations
- Single camera (monocular) — no 3D information
- Requires visible structure features for tracking
- Requires camera to be stable
- Limited to video frame rate (typically 30 fps)

### Recommended Future Enhancements
- [ ] Multi-baseline temporal evolution
- [ ] Machine learning damage classifier
- [ ] 3D reconstruction for better motion compensation
- [ ] Frequency response function (FRF) estimation
- [ ] Mode shape animation from tracking data
- [ ] Integration with IoT sensors (IMU, strain gauges)
- [ ] Historical trend analysis & predictions
- [ ] Automated alert thresholds learned from data

---

## References

- **Optical Flow**: Lucas-Kanade (cv2.calcOpticalFlowPyrLK)
- **Homography**: cv2.findHomography with RANSAC
- **Signal Processing**: scipy.signal (Butterworth, Welch PSD)
- **Damping Estimation**: Log-decrement and Hilbert envelope methods
- **Confidence Intervals**: SNR-based uncertainty propagation

---

## Support

For issues or questions:
1. Check dashboard confidence indicator for data quality
2. Review API response JSON for detailed metrics
3. Enable verbose logging in live_processor.py
4. Consult damage_hypothesis.py comments for assessment logic
5. Verify baseline exists before comparison operations

---

**Version**: 2.0 (Enhanced)  
**Last Updated**: 2025-02-25  
**Author**: Structural Vision Monitor Team
