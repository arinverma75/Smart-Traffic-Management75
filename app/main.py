"""FastAPI app: video upload, live detection, and dashboard."""
import os
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response

from app.analytics import get_recent_totals, get_traffic_state, update_history
from app.detection import get_detector, DetectionResult
from app.violations import (
    add_violations,
    create_challan,
    get_accident_alert,
    get_challans,
    get_challan_pdf,
    get_recent_violations,
    is_ambulance_priority,
    set_ambulance_manual,
)


def run_detection_on_frame(frame_bgr: np.ndarray) -> DetectionResult:
    detector = get_detector()
    return detector.detect(frame_bgr)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Pre-load YOLO model on startup
    get_detector()
    yield
    # cleanup if needed
    pass


app = FastAPI(
    title="Smart Traffic Management",
    description="YOLO-based traffic detection and analytics",
    lifespan=lifespan,
)

# Mount static files if we add any later
# app.mount("/static", StaticFiles(directory="static"), name="static")


def _template_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "templates", "index.html")


@app.get("/")
async def root():
    """Serve the dashboard."""
    path = _template_path()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return HTMLResponse(f.read())
    return HTMLResponse(
        "<h1>Smart Traffic Management</h1><p>Dashboard template not found.</p>"
    )


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "smart-traffic"}


@app.get("/api/stats")
async def stats():
    """Current counts, traffic state, alerts, and ambulance priority."""
    state = get_traffic_state()
    recent = get_recent_totals()
    from app.analytics import _history
    last_counts = _history[-1].to_dict() if _history else {}
    return JSONResponse({
        "state": {
            "level": state.level,
            "message": state.message,
            "suggestion": state.suggestion,
        },
        "recent_totals": recent,
        "by_class": last_counts.get("by_class", {}),
        "accident_alert": get_accident_alert() is not None,
        "ambulance_priority": is_ambulance_priority(),
    })


@app.post("/api/detect-frame")
async def detect_frame(file: UploadFile = File(...)):
    """Upload a single image; returns JSON with counts, violations, and annotated image."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(400, "Expected an image file")
    data = await file.read()
    buf = np.frombuffer(data, dtype=np.uint8)
    frame = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(400, "Could not decode image")
    result = run_detection_on_frame(frame)
    update_history(result.counts)
    _, jpeg = cv2.imencode(".jpg", result.frame_bgr)
    img_b64 = f"data:image/jpeg;base64,{__import__('base64').b64encode(jpeg.tobytes()).decode()}"
    add_violations(result.violations, img_b64)
    return JSONResponse({
        "counts": result.counts.to_dict(),
        "image_base64": img_b64,
        "violations": [
            {"id": v.id, "type": v.type, "vehicle_class": v.vehicle_class, "details": v.details}
            for v in result.violations
        ],
        "accident_detected": result.accident_detected,
        "ambulance_detected": result.ambulance_detected,
    })


def _generate_frames_from_video(video_bytes: bytes):
    """Yield annotated frames as JPEG from uploaded video; record violations with last frame."""
    import tempfile
    buf = np.frombuffer(video_bytes, dtype=np.uint8)
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp.flush()
        cap = cv2.VideoCapture(tmp.name)
    try:
        last_b64 = None
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            result = run_detection_on_frame(frame)
            update_history(result.counts)
            _, jpeg = cv2.imencode(".jpg", result.frame_bgr)
            last_b64 = f"data:image/jpeg;base64,{__import__('base64').b64encode(jpeg.tobytes()).decode()}"
            if result.violations:
                add_violations(result.violations, last_b64)
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
    finally:
        cap.release()


@app.post("/api/video/upload")
async def video_upload(file: UploadFile = File(...)):
    """Upload a video file; returns MJPEG stream of annotated frames."""
    if not file.filename or not any(
        file.filename.lower().endswith(ext) for ext in (".mp4", ".avi", ".mov", ".webm")
    ):
        raise HTTPException(400, "Expected a video file (e.g. .mp4)")
    data = await file.read()
    return StreamingResponse(
        _generate_frames_from_video(data),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# Optional: webcam stream (if client sends frames via websocket or we use local camera)
# Here we add a simple endpoint that uses device 0 if available
@app.get("/api/violations")
async def list_violations(limit: int = 50):
    """List recent violations (lane, no_helmet, accident)."""
    return JSONResponse({"violations": get_recent_violations(limit=limit)})


@app.post("/api/ambulance-priority")
async def ambulance_priority(enable: bool = True):  # query: ?enable=true|false
    """Set ambulance route priority (manual override)."""
    set_ambulance_manual(enable)
    return JSONResponse({"ambulance_priority": is_ambulance_priority()})


@app.post("/api/challan")
async def issue_challan(violation_id: str):
    """Create a challan for a given violation."""
    challan = create_challan(violation_id)
    if not challan:
        raise HTTPException(404, "Violation not found")
    return JSONResponse({
        "id": challan.id,
        "violation_id": challan.violation_id,
        "violation_type": challan.violation_type,
        "amount": challan.amount,
        "vehicle_info": challan.vehicle_info,
        "status": challan.status,
        "created_at": challan.created_at,
    })


@app.get("/api/challans")
async def list_challans():
    """List all issued challans."""
    return JSONResponse({"challans": get_challans()})


@app.get("/api/challan/{challan_id}/pdf")
async def download_challan_pdf(challan_id: str):
    """Download challan as PDF."""
    pdf_bytes = get_challan_pdf(challan_id)
    if not pdf_bytes:
        raise HTTPException(404, "Challan not found")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=challan_{challan_id}.pdf"},
    )


@app.get("/api/camera/stream")
async def camera_stream():
    """Live stream from default webcam with detection (if available)."""
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise HTTPException(503, "No camera available")

    def gen():
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                result = run_detection_on_frame(frame)
                update_history(result.counts)
                if result.violations:
                    _, jpeg = cv2.imencode(".jpg", result.frame_bgr)
                    img_b64 = f"data:image/jpeg;base64,{__import__('base64').b64encode(jpeg.tobytes()).decode()}"
                    add_violations(result.violations, img_b64)
                _, jpeg = cv2.imencode(".jpg", result.frame_bgr)
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
        finally:
            cap.release()

    return StreamingResponse(
        gen(), media_type="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
