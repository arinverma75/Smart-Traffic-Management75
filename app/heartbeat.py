"""Heartbeat tracker for remote systems (cameras / edge nodes).

Stores last-seen timestamps and location info, exposes helpers to
register heartbeats and to sweep systems to offline if not seen.
"""
from __future__ import annotations

import threading
import time
import json
import os
from typing import Dict, List, Optional, Tuple
import urllib.parse
import urllib.request

_lock = threading.Lock()
# system_id -> info
_systems: Dict[str, Dict] = {}
_data_file = os.path.join(os.path.dirname(__file__), "systems.json")


def _load_persisted() -> None:
    try:
        if os.path.isfile(_data_file):
            with open(_data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    with _lock:
                        _systems.clear()
                        for k, v in data.items():
                            _systems[k] = v
    except Exception:
        pass


def _save_persisted() -> None:
    try:
        with _lock:
            to_write = dict(_systems)
        tmp = _data_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(to_write, f, indent=2, ensure_ascii=False)
        os.replace(tmp, _data_file)
    except Exception:
        pass


def geocode_area(area: str) -> Tuple[Optional[float], Optional[float]]:
    """Server-side geocode using Nominatim. Returns (lat, lon) or (None, None)."""
    try:
        q = urllib.parse.urlencode({"q": area, "format": "json", "limit": 1})
        url = f"https://nominatim.openstreetmap.org/search?{q}"
        req = urllib.request.Request(url, headers={"User-Agent": "smart-traffic/1.0 (email@example.com)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
            if data and isinstance(data, list):
                item = data[0]
                return float(item.get("lat")), float(item.get("lon"))
    except Exception:
        pass
    return None, None


def register_heartbeat(system_id: str, area: Optional[str] = None, lat: Optional[float] = None, lon: Optional[float] = None, meta: Optional[Dict] = None) -> None:
    """Record a heartbeat from `system_id` and update its metadata.

    `area` is a human-readable area name (e.g. "Lucknow").
    `lat`/`lon` are optional coordinates for map display.
    """
    now = time.time()
    with _lock:
        info = _systems.get(system_id, {})
        info.update({
            "id": system_id,
            "area": area or info.get("area"),
            "lat": lat if lat is not None else info.get("lat"),
            "lon": lon if lon is not None else info.get("lon"),
            "meta": (meta or info.get("meta")) or {},
            "last_seen": now,
            "status": "online",
        })
        _systems[system_id] = info
    # persist to disk
    _save_persisted()


def get_systems() -> List[Dict]:
    """Return a shallow copy list of system infos."""
    with _lock:
        return [dict(v) for v in _systems.values()]


def sweep_offline(threshold_seconds: int = 120) -> None:
    """Mark systems offline if not seen in the last `threshold_seconds`."""
    now = time.time()
    changed = False
    with _lock:
        for info in _systems.values():
            last = info.get("last_seen") or 0
            if now - last > threshold_seconds and info.get("status") != "offline":
                info["status"] = "offline"
                changed = True
    return changed


def start_sweeper(interval_seconds: int = 30, threshold_seconds: int = 120) -> threading.Thread:
    """Start a background daemon thread that calls `sweep_offline` periodically.

    Returns the started Thread object.
    """

    def _worker():
        while True:
            try:
                sweep_offline(threshold_seconds)
            except Exception:
                pass
            time.sleep(interval_seconds)

    t = threading.Thread(target=_worker, daemon=True, name="heartbeat-sweeper")
    t.start()
    return t


# Load persisted systems on import
_load_persisted()
