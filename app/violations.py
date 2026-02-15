"""Violations: lane termination, accident, no-helmet, ambulance priority; challan store."""
import io
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.config import (
    ACCIDENT_MIN_IOU,
    ACCIDENT_MIN_VEHICLES,
    CHALLAN_AMOUNTS,
    LANE_TERMINATION_ZONE,
)


@dataclass
class Violation:
    id: str
    type: str  # lane_termination | no_helmet | accident
    vehicle_class: str
    confidence: float
    bbox: tuple[float, float, float, float]
    details: str
    timestamp: float
    image_base64: Optional[str] = None


@dataclass
class Challan:
    id: str
    violation_id: str
    violation_type: str
    amount: int
    vehicle_info: str
    status: str  # pending | paid
    created_at: float
    details: str = ""


# In-memory stores (use DB in production)
_violations: list[Violation] = []
_challans: list[Challan] = []
_ambulance_detected = False
_ambulance_manual_override = False
_accident_alert: Optional[float] = None  # timestamp of last alert


def _box_center(xyxy: np.ndarray) -> tuple[float, float]:
    x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]
    return ((x1 + x2) / 2, (y1 + y2) / 2)


def _iou(box1: np.ndarray, box2: np.ndarray) -> float:
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    a1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    a2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    return inter / max(a1 + a2 - inter, 1e-6)


def check_lane_termination(
    boxes: list[tuple], frame_height: int, frame_width: int
) -> list[Violation]:
    """Flag vehicles whose center lies in the lane termination zone.
    boxes: list of (xyxy, cls_id, conf, class_name).
    """
    violations = []
    xmin, ymin, xmax, ymax = LANE_TERMINATION_ZONE
    zone_x1 = xmin * frame_width
    zone_y1 = ymin * frame_height
    zone_x2 = xmax * frame_width
    zone_y2 = ymax * frame_height
    for item in boxes:
        xyxy = item[0]
        class_name = item[3] if len(item) > 3 else "vehicle"
        cx, cy = _box_center(np.array(xyxy))
        if zone_x1 <= cx <= zone_x2 and zone_y1 <= cy <= zone_y2:
            conf = item[2] if len(item) > 2 else 0.5
            violations.append(
                Violation(
                    id=str(uuid.uuid4()),
                    type="lane_termination",
                    vehicle_class=class_name,
                    confidence=float(conf),
                    bbox=tuple(map(float, xyxy)),
                    details="Vehicle in lane termination / no-entry zone",
                    timestamp=time.time(),
                )
            )
    return violations


def check_accident(boxes: list[tuple], vehicle_class_names: set) -> Optional[Violation]:
    """Flag possible accident if many vehicles overlap (cluster).
    boxes: list of (xyxy, cls_id, conf, class_name).
    """
    if len(boxes) < ACCIDENT_MIN_VEHICLES:
        return None
    vehicle_boxes = [
        (item[0], item[1], item[2])
        for item in boxes
        if (item[3] if len(item) > 3 else "") in vehicle_class_names
    ]
    if len(vehicle_boxes) < ACCIDENT_MIN_VEHICLES:
        return None
    for i, (b1, _, c1) in enumerate(vehicle_boxes):
        overlap_count = 0
        for j, (b2, _, c2) in enumerate(vehicle_boxes):
            if i == j:
                continue
            if _iou(np.array(b1), np.array(b2)) >= ACCIDENT_MIN_IOU:
                overlap_count += 1
        if overlap_count >= ACCIDENT_MIN_VEHICLES - 1:
            return Violation(
                id=str(uuid.uuid4()),
                type="accident",
                vehicle_class="cluster",
                confidence=0.9,
                bbox=tuple(map(float, b1)),
                details="Possible accident: multiple vehicles in collision zone",
                timestamp=time.time(),
            )
    return None


def set_ambulance_detected(value: bool) -> None:
    global _ambulance_detected
    _ambulance_detected = value


def set_ambulance_manual(value: bool) -> None:
    global _ambulance_manual_override
    _ambulance_manual_override = value


def is_ambulance_priority() -> bool:
    return _ambulance_detected or _ambulance_manual_override


def set_accident_alert(ts: Optional[float] = None) -> None:
    global _accident_alert
    _accident_alert = ts or time.time()


def get_accident_alert() -> Optional[float]:
    return _accident_alert


def add_violations(new_ones: list[Violation], image_base64: Optional[str] = None) -> None:
    for v in new_ones:
        v.image_base64 = image_base64
    _violations.extend(new_ones)
    # Keep last 500
    if len(_violations) > 500:
        _violations[:] = _violations[-500:]


def get_recent_violations(limit: int = 50) -> list[dict]:
    out = []
    for v in _violations[-limit:][::-1]:
        out.append({
            "id": v.id,
            "type": v.type,
            "vehicle_class": v.vehicle_class,
            "confidence": round(v.confidence, 2),
            "details": v.details,
            "timestamp": v.timestamp,
            "has_image": bool(v.image_base64),
        })
    return out


def create_challan(violation_id: str) -> Optional[Challan]:
    v = next((x for x in _violations if x.id == violation_id), None)
    if not v:
        return None
    amount = CHALLAN_AMOUNTS.get(v.type, 500)
    if amount == 0 and v.type == "accident":
        amount = 0  # informational
    c = Challan(
        id=f"CHL-{uuid.uuid4().hex[:8].upper()}",
        violation_id=v.id,
        violation_type=v.type,
        amount=amount,
        vehicle_info=v.vehicle_class,
        status="pending",
        created_at=time.time(),
        details=v.details,
    )
    _challans.append(c)
    return c


def get_challans() -> list[dict]:
    return [
        {
            "id": c.id,
            "violation_id": c.violation_id,
            "violation_type": c.violation_type,
            "amount": c.amount,
            "vehicle_info": c.vehicle_info,
            "status": c.status,
            "created_at": c.created_at,
            "details": c.details,
        }
        for c in reversed(_challans)
    ]


def get_challan_pdf(challan_id: str) -> Optional[bytes]:
    c = next((x for x in _challans if x.id == challan_id), None)
    if not c:
        return None
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError:
        return None
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=A4)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(72, 800, "Traffic Challan / E-Challan")
    p.setFont("Helvetica", 11)
    p.drawString(72, 760, f"Challan ID: {c.id}")
    p.drawString(72, 740, f"Violation: {c.violation_type.replace('_', ' ').title()}")
    p.drawString(72, 720, f"Vehicle: {c.vehicle_info}")
    p.drawString(72, 700, f"Amount: {c.amount}")
    p.drawString(72, 680, f"Status: {c.status}")
    p.drawString(72, 660, f"Details: {c.details[:80]}...")
    p.drawString(72, 620, "Please pay at the nearest traffic office or online portal.")
    p.showPage()
    p.save()
    buf.seek(0)
    return buf.read()
