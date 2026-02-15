"""App configuration."""
import os

# YOLO model: use yolov8n for speed, yolov8m/l for accuracy
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")

# Optional: helmet detection model (YOLO trained on helmet/without_helmet)
# e.g. from Ultralytics hub or custom trained
HELMET_MODEL = os.getenv("HELMET_MODEL", "")  # leave empty to disable

# COCO classes relevant for traffic (cars, trucks, buses, motorcycles, persons)
TRAFFIC_CLASS_IDS = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    4: "airplane",
    5: "bus",
    6: "train",
    7: "truck",
}

# For display we focus on common road users
DISPLAY_CLASSES = {"person", "bicycle", "car", "motorcycle", "bus", "truck"}

# Lane termination: zone where vehicles are not allowed (e.g. end of lane / no-entry)
# Given as (x_min_ratio, y_min_ratio, x_max_ratio, y_max_ratio) 0–1 of frame
# Top strip = lane termination / no-entry zone
LANE_TERMINATION_ZONE = (0.0, 0.0, 1.0, 0.25)

# Accident detection: min overlapping vehicles to flag possible accident
ACCIDENT_MIN_VEHICLES = 3
ACCIDENT_MIN_IOU = 0.2

# Ambulance: class name we treat as ambulance (bus or add custom); or manual override
AMBULANCE_CLASS_NAMES = {"bus"}  # can add "ambulance" if using custom model

# Challan amounts (INR or any currency) per violation type
CHALLAN_AMOUNTS = {
    "lane_termination": 500,
    "no_helmet": 1000,
    "accident": 0,  # informational; fine may be set separately
    "over_speeding": 1000,
}
