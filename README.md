# Smart Traffic Management App

A web-based **smart traffic management** app that uses **YOLO** (YOLOv8) to detect vehicles and pedestrians from images, video, or a live camera. It shows real-time counts, traffic state (low / medium / high / congested), and simple suggestions for signal timing.

## Features

- **Image / Video / Camera** – Upload image or video, or use live webcam; get annotated frames with vehicle/pedestrian detection and counts.
- **Traffic analytics** – Rolling traffic state (low / medium / high / congested) and signal suggestions.
- **Lane termination** – Detects vehicles in a configured “no-entry” / lane-end zone (top of frame by default) and records violations.
- **Accident detection** – Heuristic: flags when multiple vehicles overlap (possible collision); shows an alert on the dashboard.
- **Ambulance route priority** – Detects buses (or set manually) and shows “Clear path – Ambulance priority”; manual toggle to set/clear priority.
- **Without-helmet detection** – Optional YOLO model for helmet/no-helmet; records violations when the model is configured.
- **Challan facility** – List violations, issue challans per violation, view issued challans, and **download challan as PDF**.
- **Dashboard** – Feed, traffic state, counts, alerts (accident, ambulance), violations table with “Issue Challan”, and challans table with “Download PDF”.

## Setup

1. **Python 3.10+** and a recent pip.

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

   On first run, **Ultralytics** will download the default YOLOv8n model (~6 MB) if needed.

4. **Run the app:**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

5. Open **http://localhost:8000** in your browser.

## Usage

- **Image:** Use “Image” or drag-and-drop an image. You’ll get the annotated image and updated counts/stats.
- **Video:** Use “Video” and choose a file. Processed frames will appear as they’re computed; stats update below.
- **Camera:** Click “Open camera stream” to open the live camera stream with detection in a new tab (requires a connected webcam).

## Project structure

```
Yolo/
├── app/
│   ├── __init__.py
│   ├── config.py      # YOLO, lane zone, challan amounts, optional helmet model
│   ├── detection.py   # YOLO + lane/accident/helmet/ambulance
│   ├── analytics.py   # Traffic state and suggestions
│   ├── violations.py  # Violations store, challans, PDF generation
│   ├── main.py        # FastAPI app and routes
│   └── templates/
│       └── index.html # Dashboard (feed, alerts, violations, challans)
├── requirements.txt
└── README.md
```

## Configuration

- **YOLO:** `YOLO_MODEL` (default `yolov8n.pt`). Use `yolov8m.pt` for better accuracy.
- **Helmet detection:** Set `HELMET_MODEL` to a YOLO model path that has classes like `without_helmet` / `no_helmet`. Leave unset to disable.
- **Lane termination zone:** In `app/config.py`, `LANE_TERMINATION_ZONE` is `(x_min, y_min, x_max, y_max)` as 0–1 ratios. Default top strip (0, 0, 1, 0.25) = no-entry zone.
- **Challan amounts:** Edit `CHALLAN_AMOUNTS` in `app/config.py` (e.g. `lane_termination`, `no_helmet`).

## API

- `GET /` – Dashboard.
- `GET /api/health` – Health check.
- `GET /api/stats` – Traffic state, counts, `accident_alert`, `ambulance_priority`.
- `POST /api/detect-frame` – Upload image; returns counts, violations, annotated image.
- `POST /api/video/upload` – Upload video; MJPEG stream with detection and violation recording.
- `GET /api/camera/stream` – MJPEG from webcam with detection.
- `GET /api/violations` – List recent violations.
- `POST /api/ambulance-priority?enable=true|false` – Set/clear ambulance route priority.
- `POST /api/challan?violation_id=<id>` – Issue challan for a violation.
- `GET /api/challans` – List issued challans.
- `GET /api/challan/<id>/pdf` – Download challan PDF.

## License

Use and modify as you like.
