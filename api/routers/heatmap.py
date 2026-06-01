"""
api/routers/heatmap.py — Zone-level heatmap data
Visit frequency and dwell time by zone
"""
from fastapi import APIRouter, Request
from datetime import datetime
import json
import logging
from pathlib import Path
import os

logger = logging.getLogger(__name__)
router = APIRouter()

# Zone metadata
ZONES = {
    "ENTRY": {"name": "Entry/Exit", "category": "circulation"},
    "SKINCARE": {"name": "Skincare", "category": "product"},
    "MAKEUP": {"name": "Makeup", "category": "product"},
    "FRAGRANCES": {"name": "Fragrances", "category": "product"},
    "ACCESSORIES": {"name": "Accessories", "category": "product"},
    "BILLING": {"name": "Billing Counter", "category": "checkout"},
}


@router.get("")
async def get_heatmap(request: Request, store_id: str = "STORE_BLR_002"):
    """
    GET /heatmap — Zone-level heatmap
    
    Returns zone visit frequency and avg dwell time, normalized 0-100
    Includes data_confidence flag (true if >= 20 sessions)
    """
    try:
        zone_stats = {}
        
        # Count zone events from JSONL
        events_path = Path(os.environ.get("EVENTS_OUTPUT", "events"))
        zone_visits = {z: {"count": 0, "total_dwell_ms": 0, "sessions": set()} for z in ZONES}
        
        if events_path.exists():
            for event_file in events_path.glob("*.jsonl"):
                try:
                    with open(event_file, "r") as f:
                        for line in f:
                            if not line.strip():
                                continue
                            try:
                                evt = json.loads(line)
                                zone_id = evt.get("zone_id")
                                visitor_id = evt.get("visitor_id")
                                event_type = evt.get("event_type")
                                dwell_ms = evt.get("dwell_ms", 0)
                                
                                # Count zone enters and dwells
                                if zone_id and zone_id in zone_visits:
                                    if event_type in ["ZONE_ENTER", "ZONE_DWELL"]:
                                        zone_visits[zone_id]["count"] += 1
                                        if visitor_id:
                                            zone_visits[zone_id]["sessions"].add(visitor_id)
                                        if event_type == "ZONE_DWELL":
                                            zone_visits[zone_id]["total_dwell_ms"] += dwell_ms
                            except json.JSONDecodeError:
                                continue
                except Exception as e:
                    logger.warning(f"Error reading {event_file}: {e}")
        
        # Normalize to 0-100 scale
        max_visits = max([z["count"] for z in zone_visits.values()]) or 1
        
        zones_data = []
        for zone_id, stats in zone_visits.items():
            visit_count = stats["count"]
            session_count = len(stats["sessions"])
            total_dwell = stats["total_dwell_ms"]
            
            normalized_frequency = (visit_count / max_visits * 100) if max_visits else 0
            avg_dwell_seconds = (total_dwell / 1000 / visit_count) if visit_count > 0 else 0
            
            zone_data = {
                "zone_id": zone_id,
                "zone_name": ZONES.get(zone_id, {}).get("name", zone_id),
                "visit_frequency_normalized": round(normalized_frequency, 1),
                "avg_dwell_seconds": round(avg_dwell_seconds, 1),
                "visit_count": visit_count,
                "unique_sessions": session_count,
                "data_confidence": session_count >= 20,
            }
            zones_data.append(zone_data)
        
        return {
            "store_id": store_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "zones": sorted(zones_data, key=lambda z: z["visit_frequency_normalized"], reverse=True),
            "data_source": "event_pipeline",
        }
        
    except Exception as e:
        logger.error(f"Heatmap error: {e}")
        raise
