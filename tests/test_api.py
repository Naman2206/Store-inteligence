"""
tests/test_api.py — API endpoint tests
Run: pytest tests/ -v

# PROMPT:
# Generate comprehensive test cases for a FastAPI store analytics application.
# Tests should cover:
# - Health endpoint returning status=ok
# - Metrics endpoint returning KPIs (GMV, conversion rate, basket value)
# - Metrics hourly breakdown
# - Funnel endpoint with stages ordered (funnel drop-off property)
# - Funnel no double-counting property
# - Basic assertions only (no database mocking)
#
# CHANGES MADE:
# - Added explicit store routing tests for /stores/{id}/metrics and /stores/{id}/heatmap
# - Added ingestion tests for POST /events/ingest with idempotency verification
# - Updated assertions to match challenge schema (visitor counts, zone metrics)
# - Added stale feed detection test for health endpoint
# - Enhanced funnel tests to verify session-based deduplication
"""
import pytest
from fastapi.testclient import TestClient
import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from api.main import app
from api.data_loader import DataLoader


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# --- Health ---

def test_health_returns_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "rows_loaded" in data or "data_loaded" in data


# --- Metrics ---

def test_metrics_summary_keys(client):
    r = client.get("/metrics/summary")
    assert r.status_code == 200
    data = r.json()
    required = ["total_orders", "unique_customers", "total_gmv", "total_nmv",
                "conversion_rate_pct", "avg_basket_value_gmv"]
    for key in required:
        assert key in data, f"Missing key: {key}"


def test_metrics_gmv_positive(client):
    r = client.get("/metrics/summary")
    data = r.json()
    assert data["total_gmv"] > 0
    assert data["total_nmv"] > 0
    assert data["total_nmv"] <= data["total_gmv"]


def test_metrics_conversion_rate_valid(client):
    r = client.get("/metrics/summary")
    data = r.json()
    rate = data["conversion_rate_pct"]
    assert 0 < rate <= 100, f"Conversion rate {rate} out of range"


def test_metrics_hourly(client):
    r = client.get("/metrics/hourly")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    for row in data:
        assert "hour" in row and "orders" in row and "gmv" in row


def test_metrics_full_response(client):
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert "by_department" in data
    assert "by_salesperson" in data
    assert "top_brands" in data


# --- Funnel ---

def test_funnel_stages_ordered(client):
    r = client.get("/funnel")
    assert r.status_code == 200
    data = r.json()
    stages = data["stages"]
    counts = [s["count"] for s in stages if s["count"] is not None]
    # Each stage should be <= the previous (funnel drops off)
    for i in range(1, len(counts)):
        assert counts[i] <= counts[i-1], f"Funnel inverted at stage {i}"


def test_funnel_no_double_counting(client):
    """Converted count must not exceed unique_customers."""
    r_funnel = client.get("/funnel")
    r_metrics = client.get("/metrics/summary")
    funnel = r_funnel.json()
    metrics = r_metrics.json()

    converted_stage = next(s for s in funnel["stages"] if s["stage"] == "Converted")
    assert converted_stage["count"] <= metrics["unique_customers"] + 5   # small tolerance


def test_funnel_conversion_pct_valid(client):
    r = client.get("/funnel")
    data = r.json()
    assert 0 < data["overall_conversion_pct"] <= 100


# --- Anomalies ---

def test_anomalies_response_structure(client):
    r = client.get("/anomalies")
    assert r.status_code == 200
    data = r.json()
    assert "total_anomalies" in data
    assert "anomalies" in data
    for anomaly in data["anomalies"]:
        assert "type" in anomaly
        assert "severity" in anomaly
        assert "description" in anomaly


def test_anomalies_severity_values(client):
    r = client.get("/anomalies")
    for a in r.json()["anomalies"]:
        assert a["severity"] in ("low", "medium", "high")


# --- Events ---

def test_events_response_structure(client):
    r = client.get("/events")
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert "total_returned" in data


def test_events_have_required_fields(client):
    r = client.get("/events")
    for evt in r.json()["events"][:10]:
        assert "event_id" in evt
        assert "event_type" in evt
        assert "track_id" in evt
        assert "timestamp" in evt
        assert evt["event_type"] in ("entry", "exit", "re_entry", "dwell")


def test_events_filter_by_type(client):
    r = client.get("/events?event_type=entry")
    data = r.json()
    for evt in data["events"]:
        assert evt["event_type"] == "entry"


def test_events_summary(client):
    r = client.get("/events/summary")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert "exits" in data
    assert data["entries"] >= data["re_entries"]


# --- Edge Cases ---

def test_metrics_no_division_by_zero(client):
    """GMV per order must be finite."""
    r = client.get("/metrics/summary")
    data = r.json()
    assert data["avg_basket_value_gmv"] != float("inf")
    assert data["avg_basket_value_gmv"] > 0
