"""
Integration tests: detection events ↔ API metrics/funnel.
"""
import json
import os
import pathlib
import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _entry_count_from_disk() -> int:
    events_path = pathlib.Path(os.environ.get("EVENTS_OUTPUT", "events"))
    total = 0
    for f in sorted(events_path.glob("*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                e = json.loads(line)
                if e.get("event_type") == "entry":
                    total += 1
    return total


def test_footfall_matches_entry_events_when_present(client):
    entries_disk = _entry_count_from_disk()
    if entries_disk == 0:
        pytest.skip("No detection events on disk")

    summary = client.get("/metrics/summary").json()
    assert summary["estimated_footfall"] == entries_disk


def test_funnel_footfall_matches_entries(client):
    entries_disk = _entry_count_from_disk()
    if entries_disk == 0:
        pytest.skip("No detection events on disk")

    funnel = client.get("/funnel").json()
    footfall_stage = next(s for s in funnel["stages"] if s["stage"] == "Footfall")
    assert footfall_stage["count"] == entries_disk


def test_event_ids_unique_in_jsonl():
    events_path = pathlib.Path(os.environ.get("EVENTS_OUTPUT", "events"))
    files = list(events_path.glob("*.jsonl"))
    if not files:
        pytest.skip("No event files")

    seen = set()
    dupes = []
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                eid = json.loads(line)["event_id"]
                if eid in seen:
                    dupes.append(eid)
                seen.add(eid)
    assert not dupes, f"Duplicate event_id values: {dupes[:5]}"


def test_re_entries_lte_entries(client):
    summary = client.get("/events/summary").json()
    assert summary["re_entries"] <= summary["entries"]
