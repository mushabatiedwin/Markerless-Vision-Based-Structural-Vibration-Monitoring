"""
Enhanced FastAPI server for Structural Vision Monitor
=====================================================
Endpoints for real-time monitoring, baseline management, event tracking,
damage assessment, and confidence metrics.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import threading
import time
import cv2

import live_processor

app = FastAPI(
    title="Structural Vision Monitor",
    version="2.0 (Enhanced)",
    description="Advanced structural health monitoring with damage detection"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    print("[API] Starting enhanced structural monitoring system...")
    live_processor.start_processing(camera_index=0)


# ---------------------------------------------------------------------------
# Health & Status
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0"}


# ---------------------------------------------------------------------------
# Core Metrics
# ---------------------------------------------------------------------------

@app.get("/metrics")
def get_metrics():
    """Get current vibration metrics (core data)."""
    metrics = live_processor.get_latest_metrics()
    
    # Return core metrics, remove large buffers
    core = {
        "frequency": metrics.get("frequency"),
        "damping": metrics.get("damping"),
        "rms": metrics.get("rms"),
        "snr": metrics.get("snr"),
        "status": metrics.get("status"),
    }
    return JSONResponse(content=core)


@app.get("/signal")
def get_signal(n: int = Query(60, ge=10, le=300)):
    """Get last N displacement samples for live waveform."""
    m = live_processor.get_latest_metrics()
    buf = m.get("signal_buffer", [])
    return JSONResponse(content={"samples": buf[-n:]})


@app.get("/video_feed")
def video_feed():
    """MJPEG stream of annotated camera feed."""
    return StreamingResponse(
        _frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


def _frame_generator():
    while True:
        frame = live_processor.get_latest_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )
        time.sleep(1.0 / 30)


# ---------------------------------------------------------------------------
# Spectral Analysis
# ---------------------------------------------------------------------------

@app.get("/spectral_peaks")
def get_spectral_peaks():
    """Get top spectral peaks and their characteristics."""
    metrics = live_processor.get_latest_metrics()
    peaks = metrics.get("spectral_peaks", [])
    
    return JSONResponse(content={
        "peaks": peaks,
        "count": len(peaks)
    })


# ---------------------------------------------------------------------------
# Baseline Management
# ---------------------------------------------------------------------------

@app.get("/baselines")
def list_baselines():
    """Get list of available baseline references."""
    baselines = live_processor.list_baselines()
    return JSONResponse(content={"baselines": baselines})


@app.post("/baselines/{name}")
def create_baseline(name: str):
    """Save current metrics as a baseline reference."""
    success = live_processor.create_baseline(name=name)
    if success:
        return JSONResponse(
            content={"success": True, "message": f"Baseline '{name}' created"},
            status_code=201
        )
    else:
        raise HTTPException(status_code=400, detail="Failed to create baseline")


@app.get("/baselines/{name}")
def get_baseline(name: str):
    """Retrieve a saved baseline."""
    baseline = live_processor.load_baseline(name=name)
    if baseline:
        return JSONResponse(content=baseline)
    else:
        raise HTTPException(status_code=404, detail=f"Baseline '{name}' not found")


@app.delete("/baselines/{name}")
def delete_baseline(name: str):
    """Delete a baseline."""
    success = live_processor.reset_baseline(name=name)
    if success:
        return JSONResponse(content={"success": True, "message": f"Baseline '{name}' deleted"})
    else:
        raise HTTPException(status_code=400, detail="Failed to delete baseline")


# ---------------------------------------------------------------------------
# Baseline Comparison
# ---------------------------------------------------------------------------

@app.get("/baseline_comparison")
def get_baseline_comparison(baseline: str = Query("default")):
    """
    Compare current metrics against a baseline.
    
    Query Parameters:
    - baseline: name of baseline to compare against (default: "default")
    
    Returns:
    - deviations: dict of percent changes for each metric
    - severity: 'normal' | 'warning' | 'critical'
    - max_deviation: largest percent change
    - alerts: list of alert messages
    """
    metrics = live_processor.get_latest_metrics()
    comparison = metrics.get("baseline_comparison")
    
    if comparison is None:
        return JSONResponse(
            content={
                "deviations": {},
                "severity": "unknown",
                "max_deviation": 0.0,
                "alerts": ["Baseline comparison not yet available"]
            }
        )
    
    return JSONResponse(content=comparison)


# ---------------------------------------------------------------------------
# Event Detection
# ---------------------------------------------------------------------------

@app.get("/events")
def get_events():
    """Get summary of detected events (impacts, anomalies, etc.)."""
    metrics = live_processor.get_latest_metrics()
    event_data = metrics.get("event_detection", {})
    
    return JSONResponse(content={
        "impact_detection": event_data.get("impact", {}),
        "event_summary": event_data.get("event_summary", {}),
    })


@app.get("/events/recent")
def get_recent_events(lookback_seconds: float = Query(60.0, ge=1.0)):
    """
    Get recent high-severity events (impacts).
    
    Query Parameters:
    - lookback_seconds: how far back to look (default: 60s)
    """
    metrics = live_processor.get_latest_metrics()
    event_data = metrics.get("event_detection", {})
    event_summary = event_data.get("event_summary", {})
    
    return JSONResponse(content={
        "lookback_seconds": lookback_seconds,
        "total_recorded_events": event_summary.get("total_events", 0),
        "recent_events": event_summary.get("recent_events", 0),
        "high_severity_count": event_summary.get("high_severity", 0),
        "medium_severity_count": event_summary.get("medium_severity", 0),
        "latest_event": event_summary.get("latest_event"),
    })


# ---------------------------------------------------------------------------
# Damage Assessment
# ---------------------------------------------------------------------------

@app.get("/damage_assessment")
def get_damage_assessment():
    """
    Get comprehensive damage hypothesis assessment.
    
    Returns:
    - crack_likelihood: float (0-1, probability)
    - damage_type: 'none' | 'surface_crack' | 'deep_crack' | 'fracture' | 'unknown'
    - damage_indicator: overall damage score (0-1)
    - warning_level: 'none' | 'caution' | 'alert' | 'critical'
    - indicators: breakdown of individual damage signatures
    - recommendations: actionable guidance
    """
    metrics = live_processor.get_latest_metrics()
    damage = metrics.get("damage_assessment", {})
    
    return JSONResponse(content=damage)


# ---------------------------------------------------------------------------
# Confidence & Uncertainty
# ---------------------------------------------------------------------------

@app.get("/confidence")
def get_confidence_metrics():
    """
    Get measurement confidence and uncertainty estimates.
    
    Returns:
    - overall_confidence: float (0-1)
    - frequency_confidence, damping_confidence, rms_confidence: per-metric confidence
    - tracking_confidence: feature tracking robustness
    - uncertainty_bounds: 95% CI for each metric
    - quality_score: 'excellent' | 'good' | 'fair' | 'poor'
    - warnings: list of issues affecting confidence
    """
    metrics = live_processor.get_latest_metrics()
    confidence = metrics.get("confidence_metrics", {})
    
    # Remove redundant fields for API response
    response = {
        "overall_confidence": confidence.get("overall_confidence", 0.5),
        "frequency_confidence": confidence.get("frequency_confidence", 0.5),
        "damping_confidence": confidence.get("damping_confidence", 0.5),
        "rms_confidence": confidence.get("rms_confidence", 0.5),
        "tracking_confidence": confidence.get("tracking_confidence", 0.5),
        "quality_score": confidence.get("quality_score", "unknown"),
        "num_warnings": confidence.get("num_issues", 0),
        "warnings": confidence.get("warnings", []),
        "uncertainty_bounds": confidence.get("uncertainty_bounds", {}),
    }
    
    return JSONResponse(content=response)


# ---------------------------------------------------------------------------
# Comprehensive Dashboard Data
# ---------------------------------------------------------------------------

@app.get("/dashboard")
def get_dashboard_data():
    """
    Get all data needed for the dashboard in a single request.
    Useful for periodic dashboard refreshes.
    """
    metrics = live_processor.get_latest_metrics()
    
    dashboard = {
        "metrics": {
            "frequency": metrics.get("frequency"),
            "damping": metrics.get("damping"),
            "rms": metrics.get("rms"),
            "snr": metrics.get("snr"),
            "status": metrics.get("status"),
        },
        "baseline_comparison": metrics.get("baseline_comparison", {}),
        "damage_assessment": metrics.get("damage_assessment", {}),
        "confidence": metrics.get("confidence_metrics", {}),
        "events": metrics.get("event_detection", {}),
        "spectral_peaks": metrics.get("spectral_peaks", []),
    }
    
    return JSONResponse(content=dashboard)


# ---------------------------------------------------------------------------
# HTML Dashboard
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())
