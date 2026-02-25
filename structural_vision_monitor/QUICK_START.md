# Quick Start Guide — Enhanced Structural Vision Monitor

## What's New? (4 Major Features Added)

### 1. **Damage/Crack Detection** 🔍
- Detects structural damage through 6 independent indicators
- Classifies damage type: surface crack / deep crack / fracture
- Provides severity level: caution / alert / critical
- Generates actionable recommendations

### 2. **Baseline Comparison** 📊
- Save a "healthy state" baseline
- Compare current metrics against baseline
- Track percent deviations in real-time
- Automatic severity classification

### 3. **Impact Detection** 💥
- Detects sudden impacts and shocks
- Measures impact magnitude and severity
- Maintains event history with timestamps
- Identifies anomalous behavior patterns

### 4. **Confidence Indicators** ⚠️
- Quantifies measurement uncertainty
- Shows confidence for each metric (frequency, damping, RMS)
- Provides uncertainty bounds (95% CI)
- Warns when data quality is poor

---

## Installation (30 seconds)

```bash
# 1. Install dependencies
pip install numpy opencv-python scipy fastapi uvicorn matplotlib

# 2. Create directory structure (if not exists)
mkdir -p templates static baselines results data

# 3. Copy files
cp *.py templates/ static/ .
cp index.html templates/
cp style.css static/

# 4. Start server
uvicorn api:app --reload --port 8000

# 5. Open browser
# http://localhost:8000
```

---

## First Run (3 minutes)

### Step 1: Start Monitoring
```
Dashboard opens → "Connecting..." badge
Wait 30 seconds → "Live" badge appears
```

### Step 2: Establish Baseline
```
1. Point camera at structure
2. Wait 1-2 minutes (let metrics stabilize)
3. Click "📌 Save Baseline" button
4. Name it "healthy_state" or similar
```

### Step 3: Monitor for Changes
```
Dashboard auto-updates every 1-2 seconds
- Frequency/Damping/RMS values
- Confidence gauge (target: >70%)
- Baseline deviations (target: <15%)
- Damage likelihood (target: <30%)
- Recent events (should be 0)
```

---

## Understanding the Dashboard

### Core Metrics (Top Right)
```
Frequency: 5.23 Hz (85% conf)
Damping:   0.042 (70% conf)
RMS:       2.15 px (90% conf)
Health:    Stable
```

### Confidence Card (Left, Row 2)
```
Overall Confidence: ███████░░ 82%
- Quality: Good ✓
- Warnings: 1 (Low SNR reduces damping)
```

### Baseline Comparison (Right, Row 2)
```
Severity: NORMAL (green)
Max Deviation: 8.3%

Deviations:
  frequency: +3.2%
  damping:   -2.1%
  rms:       +8.3%
  snr:       -1.5%
```

### Damage Assessment (Left, Row 3)
```
Crack Likelihood: ████░░░░░░ 35%
Type:  NONE (green badge)
Alert: CAUTION (yellow)

Recommendations:
  ✓ Structure appears healthy
  → Continue routine monitoring
```

### Events (Right, Row 3)
```
Recent Events:    0
High Severity:    0
Latest Impact:    None detected
```

---

## Common Scenarios

### ✅ Healthy Structure
```
Confidence: >80% (excellent)
Baseline:   <10% deviation
Damage:     <20% likelihood
Events:     0 impacts
→ All good! Routine monitoring sufficient
```

### ⚠️ Minor Changes
```
Confidence: 60-80% (good)
Baseline:   10-25% deviation
Damage:     20-40% likelihood (surface_crack)
Alert:      CAUTION
→ Schedule visual inspection, monitor trend
```

### 🚨 Significant Damage
```
Confidence: 70%+ (even with uncertainty)
Baseline:   >25% deviation in multiple metrics
Damage:     >50% likelihood (deep_crack)
Alert:      CRITICAL
→ Escalate to structural engineer, consider restrictions
```

### 💥 Impact Detected
```
Events:           Recent impact logged
High Severity:    1 or more events
Latest Impact:    Magnitude, time, severity
→ Investigate cause, determine if structural impact occurred
```

---

## Confidence Levels Explained

### Why Confidence < 70%?

| Issue | Cause | Fix |
|-------|-------|-----|
| Poor SNR | Weak signal, too much noise | Improve lighting, focus camera |
| Unstable Freq | Tracking drift, too few features | Verify 100+ features tracked |
| Low Damping Confidence | Hard to estimate accurately | Accept as inherent limitation |
| Non-stationary Signal | Changing conditions | Wait for stabilization |

### Confidence Bounds
Each metric has uncertainty bounds (95% CI):
```
Frequency: 5.23 Hz (±0.15 Hz)  → true value likely in [5.08, 5.38]
Damping:   0.042 (±0.008)      → true value likely in [0.034, 0.050]
RMS:       2.15 px (±0.28 px)  → true value likely in [1.87, 2.43]
```

---

## Creating & Managing Baselines

### Create New Baseline
```
1. Click "📌 Save Baseline"
2. Enter name: "healthy_2024-02", "post_repair", etc.
3. Baseline saved to ./baselines/{name}.json
```

### Use Different Baseline
```
1. Click dropdown menu next to baseline button
2. Select from: "default", "baseline_14_30", ...
3. Comparison updates to selected baseline
```

### Delete Baseline
```
1. Click dropdown → select baseline
2. (No delete button—manually remove from ./baselines/ folder)
   or use API: DELETE /baselines/{name}
```

---

## API Quick Reference

### Basic Endpoints
```
GET /health                    Check if server is running
GET /metrics                   Current metrics (frequency, damping, rms, snr)
GET /signal?n=60              Last 60 displacement samples
GET /spectral_peaks           Top 5 frequency peaks with Q-factors
```

### Baseline Endpoints
```
GET /baselines                 List all baselines
POST /baselines/my_baseline    Create baseline from current state
GET /baselines/my_baseline     Get saved baseline data
DELETE /baselines/my_baseline  Delete baseline
GET /baseline_comparison?baseline=my_baseline
                              Compare current to baseline
```

### Advanced Endpoints
```
GET /damage_assessment        Damage likelihood & recommendations
GET /events                   Impact detection summary
GET /events/recent?lookback_seconds=60
                             Recent impacts in last 60 seconds
GET /confidence               Measurement confidence & uncertainty
GET /dashboard                All dashboard data in one request
```

---

## Troubleshooting

### Dashboard Says "Offline"
- Check if server is running: `uvicorn api:app --reload`
- Verify firewall allows port 8000
- Check browser console (F12) for errors

### Features Not Being Tracked
- Ensure good lighting on structure
- Make sure structure has visible features (texture, corners)
- If ROI is used, verify it covers the target area
- Check camera focus

### Confidence Too Low (<60%)
```
Try:
1. Move camera closer (better resolution)
2. Improve lighting
3. Reduce camera motion (use tripod)
4. Wait longer for stabilization (2-3 min)
5. Check SNR value - should be >10 dB
```

### Baseline Comparison Not Working
```
Check:
1. Baseline file exists: ./baselines/{name}.json
2. At least 30 seconds elapsed since startup
3. Baseline dropdown shows the baseline you created
4. API /baselines endpoint returns your baseline
```

### False Damage Alerts
```
Before taking action:
1. Review all 6 damage indicators (not just likelihood)
2. Check confidence level (if <60%, data may be unreliable)
3. Verify camera is stable (impacts from vibration ≠ structural damage)
4. Perform visual inspection before structural action
```

### Event Detection Not Working
```
Ensure:
1. Signal has sufficient amplitude (RMS > 1 px)
2. Analysis window is large enough (150+ samples ≈ 5 seconds)
3. Impact is sharp and distinct (not slow drift)
4. SNR is reasonable (>5 dB)
```

---

## Example Workflow

```
Time    Action                    Dashboard Shows
────────────────────────────────────────────────────────
T+0     Start monitoring          "Connecting..."
T+30s   Stabilization             "Live", metrics updating
T+2min  Establish baseline        Frequency: 5.2 Hz, Confidence: 85%
        Click "📌 Save Baseline"  Baseline saved, select dropdown
        Name: "safe_state"        Baseline Comparison: 0% deviation
────────────────────────────────────────────────────────
T+5min  Normal operation          All metrics stable
        (continuous monitoring)   Deviations: <10%
                                  Damage: <20%
────────────────────────────────────────────────────────
T+15min IMPACT EVENT              ⚠ Damage: 45% likelihood
                                  Type: surface_crack
                                  Alert: ALERT
                                  Event: 1 high-severity impact
        Check structure           Visual inspection
        Frequency down 12%        Adjust baseline if appropriate
        Damping up 25%
────────────────────────────────────────────────────────
T+30min Stable again              Metrics settling
        Create new baseline       "safe_state_post_impact"
        if structure still OK     for future reference
```

---

## File Locations

```
./
├── api.py                 FastAPI server (START THIS)
├── live_processor.py      Real-time monitoring pipeline
├── baseline_manager.py    Baseline storage & comparison
├── event_detector.py      Impact & anomaly detection
├── damage_hypothesis.py   Damage assessment engine
├── confidence_metrics.py  Uncertainty quantification
├── signal_analysis.py     FFT, filtering, etc.
├── feature_tracker.py     Optical flow tracking
├── motion_compensation.py Homography-based compensation
├── calibration.py         Camera calibration
├── main.py               Offline video analysis
├── utils.py              Utilities
├── templates/
│   └── index.html        Dashboard UI
├── static/
│   └── style.css         Dashboard styles
├── baselines/            Baseline files (auto-created)
│   ├── default.json
│   ├── safe_state.json
│   └── ...
├── data/
│   └── test_video.mp4    Test video (if available)
└── results/              Analysis output directory
```

---

## Next Steps

1. **Install & Run** → Follow installation section
2. **Create Baseline** → Establish "healthy state"
3. **Monitor Trends** → Watch dashboard for patterns
4. **Compare Baselines** → Test different references
5. **Review Documentation** → Read `ENHANCED_FEATURES.md`
6. **Tune Parameters** → Adjust detection thresholds if needed

---

## Support Resources

- **ENHANCED_FEATURES.md** — Complete feature documentation (300+ lines)
- **README_IMPLEMENTATION.md** — Technical implementation details
- **Code Comments** — See damage_hypothesis.py, confidence_metrics.py
- **Dashboard Help** → Hover over metric cards for tooltips

---

## Performance Tips

- **Camera Focus** → Use autofocus or manual adjustment
- **Lighting** → Ensure consistent illumination
- **Features** → Prefer textured surfaces (avoid uniform walls)
- **Resolution** → 640×480 minimum, 1280×720 recommended
- **FPS** → 30 fps typical, 15+ fps minimum

---

## License & Attribution

Structural Vision Monitor v2.0 (Enhanced)  
Advanced monitoring features implemented February 2025

---

**Ready to start? Run:** `uvicorn api:app --reload --port 8000` ✅
