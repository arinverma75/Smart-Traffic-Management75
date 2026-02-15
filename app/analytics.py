"""Traffic analytics: congestion level and suggestions."""
from collections import deque
from dataclasses import dataclass

from app.detection import TrafficCounts


@dataclass
class TrafficState:
    """Current traffic state for a junction/stream."""
    level: str  # "low" | "medium" | "high" | "congested"
    message: str
    suggestion: str


# Rolling window of recent counts for smoothing
_history: deque[TrafficCounts] = deque(maxlen=30)


def update_history(counts: TrafficCounts) -> None:
    _history.append(counts)


def get_traffic_state() -> TrafficState:
    """Derive congestion level and suggestion from recent counts."""
    if not _history:
        return TrafficState(
            level="low",
            message="No data yet",
            suggestion="Start a video or camera feed to analyze traffic.",
        )
    recent = list(_history)
    avg_total = sum(c.total for c in recent) / len(recent)
    if avg_total < 5:
        return TrafficState(
            level="low",
            message=f"Light traffic (~{int(avg_total)} objects)",
            suggestion="Normal signal timing is fine.",
        )
    if avg_total < 15:
        return TrafficState(
            level="medium",
            message=f"Moderate traffic (~{int(avg_total)} objects)",
            suggestion="Consider slightly longer green for main flow.",
        )
    if avg_total < 30:
        return TrafficState(
            level="high",
            message=f"Heavy traffic (~{int(avg_total)} objects)",
            suggestion="Extend green phase; monitor pedestrian crossings.",
        )
    return TrafficState(
        level="congested",
        message=f"Congested (~{int(avg_total)} objects)",
        suggestion="Maximize green for dominant direction; consider overflow lanes.",
    )


def get_recent_totals() -> list[int]:
    """Last N total counts for charts."""
    return [c.total for c in _history]
