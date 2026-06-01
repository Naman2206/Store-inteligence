"""
/events — Structured detection events from CCTV pipeline.
Each event has: event_id, type, timestamp, track_id, zone, confidence.
In production, populated by detection/pipeline.py writing to events/*.jsonl
Here we generate realistic synthetic events aligned to actual transaction hours.
"""
from fastapi import APIRouter, Request, Query
from datetime import datetime, date
import json, os, pathlib

router = APIRouter()

EVENTS_PATH = pathlib.Path(os.environ.get("EVENTS_OUTPUT", "events"))


@router.get("")
async def get_events(
    request: Request,
    event_type: str = Query(None, description="Filter: entry|exit|dwell|re_entry"),
    limit: int = Query(100, le=500),
):
    events = _load_events(event_type, limit)
    return {
        "store": "Brigade_Bangalore",
        "date": "2026-04-10",
        "total_returned": len(events),
        "events": events,
    }


@router.get("/summary")
async def get_events_summary(request: Request):
    events = _load_events()
    from collections import Counter
    type_counts = Counter(e["event_type"] for e in events)
    return {
        "total_events": len(events),
        "entries": type_counts.get("entry", 0),
        "exits": type_counts.get("exit", 0),
        "re_entries": type_counts.get("re_entry", 0),
        "dwell_alerts": type_counts.get("dwell", 0),
        "unique_tracks": len({e["track_id"] for e in events}),
    }


def _load_events(event_type: str = None, limit: int = 500) -> list:
    """Load from JSONL files if present, else return synthetic events."""
    all_events = []
    if EVENTS_PATH.exists():
        for f in sorted(EVENTS_PATH.glob("*.jsonl")):
            with open(f) as fh:
                for line in fh:
                    try:
                        all_events.append(json.loads(line))
                    except Exception:
                        pass

    if not all_events:
        all_events = _synthetic_events()

    if event_type:
        all_events = [e for e in all_events if e["event_type"] == event_type]

    return all_events[:limit]


def _synthetic_events() -> list:
    """
    Generate realistic entry/exit events aligned to the 24 transaction orders
    spread across hours 12–21 with proper re-entry simulation.
    """
    import random, hashlib
    random.seed(42)

    # Hours with actual transaction orders from data
    hourly_orders = {12:2,13:2,14:1,15:3,16:3,17:2,18:3,19:5,20:1,21:2}
    events = []
    track_counter = 0
    eid = 1000

    for hour, n_orders in hourly_orders.items():
        # ~35% more walkins than buyers
        n_visitors = int(n_orders * 1.35)
        for i in range(n_visitors):
            track_counter += 1
            tid = f"T{track_counter:04d}"
            minute_in = random.randint(0, 55)
            dwell = random.randint(8, 45)
            minute_out = min(minute_in + dwell, 59)

            events.append({
                "event_id": f"EVT{eid:06d}",
                "event_type": "entry",
                "track_id": tid,
                "timestamp": f"2026-04-10T{hour:02d}:{minute_in:02d}:00",
                "zone": "entrance",
                "confidence": round(random.uniform(0.82, 0.99), 3),
                "is_staff": False,
            })
            eid += 1

            events.append({
                "event_id": f"EVT{eid:06d}",
                "event_type": "exit",
                "track_id": tid,
                "timestamp": f"2026-04-10T{hour:02d}:{minute_out:02d}:00",
                "zone": "entrance",
                "confidence": round(random.uniform(0.82, 0.99), 3),
                "dwell_minutes": dwell,
                "is_staff": False,
            })
            eid += 1

            # ~15% re-entry
            if random.random() < 0.15:
                minute_re = min(minute_out + random.randint(3, 10), 59)
                events.append({
                    "event_id": f"EVT{eid:06d}",
                    "event_type": "re_entry",
                    "track_id": tid,
                    "timestamp": f"2026-04-10T{hour:02d}:{minute_re:02d}:00",
                    "zone": "entrance",
                    "confidence": round(random.uniform(0.75, 0.95), 3),
                    "is_staff": False,
                })
                eid += 1

    # Add 5 staff entries at start of day
    for i in range(5):
        events.insert(i, {
            "event_id": f"EVT{900+i:06d}",
            "event_type": "entry",
            "track_id": f"STAFF{i+1:02d}",
            "timestamp": f"2026-04-10T10:0{i}:00",
            "zone": "entrance",
            "confidence": 0.99,
            "is_staff": True,
        })

    return sorted(events, key=lambda e: e["timestamp"])
