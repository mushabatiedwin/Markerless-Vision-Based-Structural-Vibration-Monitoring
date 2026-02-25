"""
FastAPI server for Structural Vision Monitor
============================================
Endpoints:
  GET /               — Dashboard UI
  GET /video_feed     — MJPEG camera stream
  GET /metrics        — Latest vibration metrics (JSON)
  GET /signal         — Last N displacement samples for live chart
  GET /health         — Liveness check
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
import threading
import time
import cv2

import live_processor

app = FastAPI(title="Structural Vision Monitor", version="1.0")

# Allow frontend dev server to call API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ---------------------------------------------------------------------------
# Background processor startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event():
    print("[API] Starting background processor...")
    live_processor.start_processing(camera_index=0)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def get_metrics():
    metrics = live_processor.get_latest_metrics()
    # Remove signal_buffer from metrics response (use /signal endpoint instead)
    metrics.pop("signal_buffer", None)
    return JSONResponse(content=metrics)


@app.get("/signal")
def get_signal(n: int = 60):
    """Return last N displacement samples for the live waveform chart."""
    m = live_processor.get_latest_metrics()
    buf = m.get("signal_buffer", [])
    return JSONResponse(content={"samples": buf[-n:]})


@app.get("/video_feed")
def video_feed():
    """MJPEG stream of annotated frames."""
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


@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open("templates/index.html", "r") as f:
        return HTMLResponse(content=f.read())
