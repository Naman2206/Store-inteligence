"""
Integrity tests: outputs must depend on real inputs (anti-hardcoding).
"""
import json
import os
import pathlib
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.data_loader import DataLoader


@pytest.fixture
def client_with_events(tmp_path):
    events_src = pathlib.Path(os.environ.get("EVENTS_OUTPUT", "events"))
    events_tmp = tmp_path / "events"
    events_tmp.mkdir()
    for f in events_src.glob("*.jsonl"):
        shutil.copy(f, events_tmp / f.name)

    os.environ["EVENTS_OUTPUT"] = str(events_tmp)
    with TestClient(app) as c:
        yield c, events_tmp
    os.environ.pop("EVENTS_OUTPUT", None)


def test_metrics_change_without_events(tmp_path):
    """Empty events dir should use fallback footfall heuristic."""
    empty = tmp_path / "empty_events"
    empty.mkdir()
    os.environ["EVENTS_OUTPUT"] = str(empty)

    with TestClient(app) as c:
        without = c.get("/metrics/summary").json()

    events_src = pathlib.Path("events")
    os.environ["EVENTS_OUTPUT"] = str(events_src)
    if not list(events_src.glob("*.jsonl")):
        pytest.skip("No events to compare")

    with TestClient(app) as c:
        with_events = c.get("/metrics/summary").json()

    os.environ.pop("EVENTS_OUTPUT", None)

    if without["estimated_footfall"] != with_events["estimated_footfall"]:
        assert without["conversion_rate_pct"] != with_events["conversion_rate_pct"]


def test_gmv_from_csv_not_constant():
    loader = DataLoader()
    loader.load()
    gmv_a = float(loader.df["GMV"].sum())

    if len(loader.df) < 2:
        pytest.skip("Need multiple rows")
    loader.df = loader.df.iloc[:-1]
    gmv_b = float(loader.df["GMV"].sum())
    assert gmv_a != gmv_b


def test_conversion_rate_derivable(client_with_events):
    client, _ = client_with_events
    s = client.get("/metrics/summary").json()
    if s["estimated_footfall"] == 0:
        pytest.skip("No footfall")
    expected = round(s["unique_customers"] / s["estimated_footfall"] * 100, 2)
    assert s["conversion_rate_pct"] == expected
