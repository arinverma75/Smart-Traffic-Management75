# What Was Used to Build This Project

A list of technologies, libraries, and tools used in the **Smart Traffic Management** app.

---

## Programming Language
- **Python 3.10+** – main language for backend and logic

---

## Core Dependencies (in `requirements.txt`)

| Package | Purpose |
|--------|---------|
| **ultralytics** (≥8.0.0) | YOLOv8 – object detection (vehicles, persons, etc.) |
| **opencv-python-headless** (≥4.8.0) | Image/video handling, drawing boxes, camera and video I/O |
| **fastapi** (≥0.104.0) | Web API framework – routes, request/response, docs |
| **uvicorn** (≥0.24.0) | ASGI server to run the FastAPI app |
| **python-multipart** (≥0.0.6) | Handle file uploads (images, videos) in FastAPI |
| **numpy** (≥1.24.0) | Arrays and math (image buffers, bbox math, IoU) |
| **aiofiles** (≥23.2.0) | Async file I/O (available for future use) |
| **reportlab** (≥4.0.0) | Generate PDF challans |

---

## Indirect Dependencies (pulled in by the above)

- **torch** (PyTorch) – used by Ultralytics/YOLO for inference  
- **torchvision** – vision utilities for YOLO  
- **Pillow** – image handling (used by Ultralytics)  
- **matplotlib** – plotting (used by Ultralytics)  
- **scipy** – scientific routines (used by Ultralytics)  
- **pydantic** – request/response validation (used by FastAPI)  
- **starlette** – ASGI toolkit (used by FastAPI)  

---

## Frontend (no separate build)
- **HTML5** – structure of the dashboard  
- **CSS3** – layout, colors, cards, tables, buttons  
- **JavaScript (vanilla)** – fetch API, file upload, polling stats, violations, challans  

No React/Vue or npm; everything is served by FastAPI (single HTML + inline JS/CSS).

---

## AI / ML
- **YOLOv8** (via Ultralytics) – pre-trained COCO model for:
  - car, truck, bus, motorcycle, bicycle, person
- **Optional:** custom YOLO model for helmet / no-helmet (if `HELMET_MODEL` is set)

---

## Concepts / Techniques Used
- Object detection (bounding boxes, confidence)
- Lane zone check (vehicle center inside a rectangle)
- Accident heuristic (multiple boxes overlapping – IoU)
- Violations store (in-memory list)
- Challan generation (amounts by violation type, PDF export)
- Ambulance priority (detect bus or manual toggle)
- MJPEG streaming for live camera and processed video

---

## Project Structure (what’s in the repo)
- **app/config.py** – YOLO model path, lane zone, challan amounts, helmet model  
- **app/detection.py** – YOLO inference, lane/accident/helmet checks, ambulance flag  
- **app/analytics.py** – traffic state (low/medium/high/congested), suggestions  
- **app/violations.py** – violation types, store, challan creation, PDF  
- **app/main.py** – FastAPI app, routes, file upload, streaming  
- **app/templates/index.html** – dashboard UI  
- **requirements.txt** – Python dependencies  
- **README.md** – setup and usage  
- **TECH_STACK.md** – this file  

---

## How to Run (what you use each time)
- **Terminal** – PowerShell or Command Prompt  
- **Commands:** `cd` to project → activate `venv` → `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`  
- **Browser** – open http://localhost:8000  

---

## Summary One-Liner
**Python + FastAPI + Uvicorn + YOLOv8 (Ultralytics) + OpenCV + NumPy + Reportlab + HTML/CSS/JS** – used to build a web-based smart traffic app with detection, violations, challans, and PDF export.
