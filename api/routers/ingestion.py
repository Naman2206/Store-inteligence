"""
api/routers/ingestion.py — Event ingestion endpoint
Accepts batches of detection events and stores them
"""
from fastapi import APIRouter, Request, HTTPException
from typing import List
import logging
from api.models import StoreEvent

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory event store (deduplication by event_id)
_event_store: set[str] = set()


@router.post("")
async def ingest_events(request: Request, events_batch: dict):
    """
    POST /events/ingest — Ingest detection events
    
    Accepts up to 500 events, deduplicates by event_id, returns structured response.
    Idempotent: safe to call twice with same payload.
    """
    try:
        events_list = events_batch.get("events", [])
        if not isinstance(events_list, list):
            raise HTTPException(status_code=400, detail="events field must be a list")
        
        if len(events_list) > 500:
            raise HTTPException(status_code=400, detail="Maximum 500 events per batch")
        
        ingested = 0
        duplicates = 0
        errors = []
        
        for idx, evt_dict in enumerate(events_list):
            try:
                # Validate event structure
                event_id = evt_dict.get("event_id")
                if not event_id:
                    errors.append({"index": idx, "error": "Missing event_id"})
                    continue
                
                # Check for duplicate
                if event_id in _event_store:
                    duplicates += 1
                    continue
                
                # Validate required fields
                required_fields = ["store_id", "camera_id", "visitor_id", "event_type", 
                                 "timestamp", "dwell_ms", "is_staff", "confidence"]
                for field in required_fields:
                    if field not in evt_dict:
                        errors.append({"index": idx, "error": f"Missing field: {field}"})
                        continue
                
                # Store event
                _event_store.add(event_id)
                ingested += 1
                logger.debug(f"Ingested event: {event_id} type={evt_dict.get('event_type')}")
                
            except Exception as e:
                errors.append({"index": idx, "error": str(e)})
        
        response = {
            "status": "partial_success" if errors else "success",
            "ingested_count": ingested,
            "duplicate_count": duplicates,
            "error_count": len(errors),
            "errors": errors[:10] if errors else None,  # Limit error details
        }
        
        logger.info(f"Ingestion: {ingested} ingested, {duplicates} duplicate, {len(errors)} errors")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/deduplicated-count")
async def get_deduplicated_count():
    """Return count of unique events stored"""
    return {"unique_events_stored": len(_event_store)}
