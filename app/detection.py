"""YOLO-based traffic detection, violations (lane, accident, helmet), ambulance."""
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np
from ultralytics import YOLO

from app.config import (
    AMBULANCE_CLASS_NAMES,
    DISPLAY_CLASSES,
    HELMET_MODEL,
    LANE_TERMINATION_ZONE,
    TRAFFIC_CLASS_IDS,
    YOLO_MODEL,
)
from app.violations import (
    Violation,
    check_accident,
    check_lane_termination,
    is_ambulance_priority,
    set_accident_alert,
    set_ambulance_detected,
)

VEHICLE_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}


@dataclass
class TrafficCounts:
    """Per-class and total counts for one frame."""
    by_class: dict[str, int] = field(default_factory=dict)
    total: int = 0

    def to_dict(self) -> dict:
        return {"by_class": self.by_class, "total": self.total}


@dataclass
class DetectionResult:
    """Result of running detection on a frame."""
    frame_bgr: np.ndarray
    counts: TrafficCounts
    boxes: list  # (xyxy, class_id, conf, class_name)
    violations: list[Violation] = field(default_factory=list)
    accident_detected: bool = False
    ambulance_detected: bool = False


class TrafficDetector:
    """Runs YOLO and aggregates traffic-relevant detections + violations."""

    def __init__(self, model_path: str = YOLO_MODEL):
        self.model = YOLO(model_path)
        self._helmet_model = None
        if HELMET_MODEL:
            try:
                self._helmet_model = YOLO(HELMET_MODEL)
            except Exception:
                pass

    def _filter_traffic(self, results) -> tuple[list, TrafficCounts]:
        boxes = []
        by_class = defaultdict(int)
        names = results[0].names if results else {}
        if results and results[0].boxes is not None:
            for box in results[0].boxes:
                cls_id = int(box.cls[0])
                if cls_id not in TRAFFIC_CLASS_IDS:
                    continue
                name = names.get(cls_id, "unknown")
                if name not in DISPLAY_CLASSES and name not in TRAFFIC_CLASS_IDS.values():
                    continue
                conf = float(box.conf[0])
                xyxy = box.xyxy[0].cpu().numpy()
                boxes.append((xyxy, cls_id, conf, name))
                by_class[name] += 1
        counts = TrafficCounts(by_class=dict(by_class), total=sum(by_class.values()))
        return boxes, counts

    def _detect_helmet(self, frame_bgr: np.ndarray) -> list[Violation]:
        """Run optional helmet model; return no_helmet violations."""
        if self._helmet_model is None:
            return []
        violations = []
        try:
            r = self._helmet_model(frame_bgr, conf=0.4, verbose=False)
            if not r or not r[0].boxes:
                return []
            names = r[0].names or {}
            for box in r[0].boxes:
                cls_id = int(box.cls[0])
                name = names.get(cls_id, "").lower()
                if name in ("without_helmet", "no_helmet", "no helmet"):
                    xyxy = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    import time
                    import uuid
                    violations.append(
                        Violation(
                            id=str(uuid.uuid4()),
                            type="no_helmet",
                            vehicle_class="rider",
                            confidence=conf,
                            bbox=tuple(map(float, xyxy)),
                            details="Rider without helmet detected",
                            timestamp=time.time(),
                        )
                    )
        except Exception:
            pass
        return violations

    def detect(self, frame_bgr: np.ndarray, conf_threshold: float = 0.4) -> DetectionResult:
        """Run YOLO on a BGR frame; run violation checks; return annotated frame + counts + violations."""
        results = self.model(frame_bgr, conf=conf_threshold, verbose=False)
        boxes, counts = self._filter_traffic(results)
        out = frame_bgr.copy()
        h, w = out.shape[:2]

        # Ambulance: any bus (or ambulance class) in frame
        ambulance_detected = any(
            (item[3] if len(item) > 3 else "") in AMBULANCE_CLASS_NAMES for item in boxes
        )
        set_ambulance_detected(ambulance_detected)

        # Lane termination
        lane_violations = check_lane_termination(boxes, h, w)

        # Accident heuristic
        accident_v = check_accident(boxes, VEHICLE_CLASSES)
        accident_detected = accident_v is not None
        if accident_detected:
            set_accident_alert()

        # Helmet (optional model)
        helmet_violations = self._detect_helmet(frame_bgr)

        all_violations = lane_violations + helmet_violations
        if accident_v:
            all_violations.append(accident_v)

        # Draw boxes
        for item in boxes:
            xyxy, cls_id, conf = item[0], item[1], item[2]
            name = item[3] if len(item) > 3 else "?"
            x1, y1, x2, y2 = int(xyxy[0]), int(xyxy[1]), int(xyxy[2]), int(xyxy[3])
            color = self._color_for_class(name)
            cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
            label = f"{name} {conf:.1f}"
            cv2.putText(
                out, label, (x1, y1 - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA
            )

        # Draw lane termination zone
        xmin, ymin, xmax, ymax = LANE_TERMINATION_ZONE
        zx1, zy1 = int(xmin * w), int(ymin * h)
        zx2, zy2 = int(xmax * w), int(ymax * h)
        cv2.rectangle(out, (zx1, zy1), (zx2, zy2), (0, 0, 255), 2)
        cv2.putText(out, "NO ENTRY / LANE END", (zx1, zy1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)

        return DetectionResult(
            frame_bgr=out,
            counts=counts,
            boxes=boxes,
            violations=all_violations,
            accident_detected=accident_detected,
            ambulance_detected=is_ambulance_priority(),
        )

    def _color_for_class(self, name: str) -> tuple[int, int, int]:
        colors = {
            "car": (0, 165, 255),
            "truck": (0, 140, 255),
            "bus": (0, 215, 255),
            "motorcycle": (203, 192, 255),
            "bicycle": (255, 191, 0),
            "person": (0, 255, 0),
        }
        return colors.get(name, (200, 200, 200))


# Singleton for the app
_detector: Optional[TrafficDetector] = None


def get_detector() -> TrafficDetector:
    global _detector
    if _detector is None:
        _detector = TrafficDetector()
    return _detector
