"""
api/models.py — Pydantic models for event schema and API responses
Challenge-compliant event schema with all required fields
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid


class EventMetadata(BaseModel):
    """Event metadata sub-structure"""
    queue_depth: Optional[int] = None
    sku_zone: Optional[str] = None
    session_seq: int
    dwell_seconds: Optional[int] = None
    previous_zone_id: Optional[str] = None


class StoreEvent(BaseModel):
    """
    Event Schema (challenge-compliant)
    Emitted by detection pipeline, ingested by API
    """
    event_id: str = Field(..., description="UUID-v4, must be globally unique")
    store_id: str = Field(..., description="Store identifier from store_layout.json")
    camera_id: str = Field(..., description="Which camera produced this event")
    visitor_id: str = Field(..., description="Re-ID token, unique per visit session")
    event_type: str = Field(
        ...,
        description="ENTRY|EXIT|ZONE_ENTER|ZONE_EXIT|ZONE_DWELL|BILLING_QUEUE_JOIN|BILLING_QUEUE_ABANDON|REENTRY"
    )
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    zone_id: Optional[str] = Field(None, description="Zone identifier, null for ENTRY/EXIT")
    dwell_ms: int = Field(..., description="Duration in milliseconds; 0 for instantaneous")
    is_staff: bool = Field(..., description="Staff classification flag")
    confidence: float = Field(..., description="Detection confidence 0-1, do not suppress")
    metadata: EventMetadata


class EventIngestRequest(BaseModel):
    """Batch event ingestion request"""
    events: List[StoreEvent] = Field(..., max_items=500)


class MetricsResponse(BaseModel):
    """Store metrics response"""
    store_id: str
    timestamp: str
    unique_visitors: int
    conversion_rate_pct: float
    avg_dwell_per_zone: dict
    queue_depth_current: Optional[int]
    abandonment_rate_pct: float
    total_transactions: int


class FunnelStage(BaseModel):
    stage: str
    count: int
    drop_off_pct: Optional[float]


class FunnelResponse(BaseModel):
    store_id: str
    entry_count: int
    zone_visit_count: int
    billing_queue_count: int
    purchase_count: int
    stages: List[FunnelStage]
    overall_conversion_pct: float


class HeatmapZone(BaseModel):
    zone_id: str
    visit_frequency_normalized: float  # 0-100
    avg_dwell_seconds: float
    data_confidence: bool


class HeatmapResponse(BaseModel):
    store_id: str
    zones: List[HeatmapZone]
    timestamp: str


class Anomaly(BaseModel):
    anomaly_id: str
    anomaly_type: str
    severity: str  # INFO | WARN | CRITICAL
    description: str
    suggested_action: str
    detected_at: str


class AnomaliesResponse(BaseModel):
    store_id: str
    timestamp: str
    active_anomalies: List[Anomaly]


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    stores: dict
    stale_feeds: List[str]  # Store IDs with >10min lag
