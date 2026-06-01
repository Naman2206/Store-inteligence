from fastapi import APIRouter, Request
from datetime import datetime
import json
import logging
from pathlib import Path
import os
import time

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health(request: Request):
    """
    GET /health — Service health and data freshness
    
    Returns status, last event timestamp per store, STALE_FEED warning if >10 min lag
    """
    loader = request.app.state.loader
    store_id = "STORE_BLR_002"
    
    # Get last event timestamp from events JSONL
    events_path = Path(os.environ.get("EVENTS_OUTPUT", "events"))
    last_event_timestamp = None
    
    if events_path.exists():
        latest_time = 0
        for event_file in sorted(events_path.glob("*.jsonl"), reverse=True):
            try:
                with open(event_file, "r") as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            evt = json.loads(line)
                            ts_str = evt.get("timestamp", "")
                            # Parse ISO timestamp
                            if ts_str:
                                # Simple extraction of timestamp for comparison
                                latest_time = max(latest_time, hash(ts_str) % 1000000000)
                                last_event_timestamp = ts_str
                        except:
                            continue
            except Exception as e:
                logger.warning(f"Error reading events: {e}")
    
    # Check for stale feed (>10 min without new events)
    stale_feeds = []
    if last_event_timestamp:
        try:
            # Parse the ISO timestamp
            event_time = datetime.fromisoformat(last_event_timestamp.replace("Z", "+00:00"))
            lag_seconds = (datetime.utcnow().replace(tzinfo=None) - event_time.replace(tzinfo=None)).total_seconds()
            if lag_seconds > 600:  # 10 minutes
                stale_feeds.append({
                    "store_id": store_id,
                    "lag_seconds": int(lag_seconds),
                    "severity": "WARN" if lag_seconds < 1800 else "CRITICAL",
                })
        except:
            pass
    
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "data_loaded": {
            "rows": len(loader.df),
            "store": store_id,
        },
        "event_feed": {
            "store_id": store_id,
            "last_event_timestamp": last_event_timestamp,
            "stale_feed_warnings": stale_feeds,
        },
    }

