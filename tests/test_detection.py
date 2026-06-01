"""
tests/test_detection.py — Unit tests for detection pipeline components

# PROMPT:
# Generate unit tests for a person tracking module in a CCTV detection pipeline.
# Tests should cover:
# - Entry event creation when new centroid appears
# - No new event when same person centroid matches (within threshold distance)
# - Re-entry detection when person re-appears within 10-minute window
# - Staff detection based on timestamp before 10:30 AM cutoff
# - Graceful handling of empty frames (no crashes)
# - Track state transitions (entry → active → exit)
#
# CHANGES MADE:
# - Updated tracker initialization to use PersonTracker with visitor_id instead of track_id
# - Modified tests to check for event_type in proper challenge schema (ENTRY, EXIT, REENTRY)
# - Added zone-aware tests for zone transitions (ZONE_ENTER, ZONE_EXIT)
# - Enhanced re-entry test to use zone_map parameter and verify REENTRY event type
# - Updated staff detection test to reflect UTC-based timestamp logic
"""
import pytest
from datetime import datetime
from detection.pipeline import PersonTracker, StoreEvent


@pytest.fixture
def tracker():
    return PersonTracker()


@pytest.fixture
def zone_map():
    """Standard 3-zone layout: ENTRY, FLOOR, BILLING"""
    return {
        "ENTRY": (0, 0, 150, 480),
        "FLOOR": (150, 0, 960, 384),
        "BILLING": (150, 384, 960, 480),
    }


def test_new_entry_creates_track(tracker, zone_map):
    frame_time = datetime(2026, 4, 10, 12, 0, 0)
    events = tracker.update([(100, 200)], frame_time, zone_map)
    entry_events = [e for e in events if e.event_type == "ENTRY"]
    assert len(entry_events) == 1
    assert entry_events[0].visitor_id.startswith("VIS_")


def test_matched_centroid_no_new_event(tracker, zone_map):
    frame_time = datetime(2026, 4, 10, 12, 0, 0)
    tracker.update([(100, 200)], frame_time, zone_map)

    frame_time2 = datetime(2026, 4, 10, 12, 0, 1)
    events = tracker.update([(105, 198)], frame_time2, zone_map)   # close centroid = same person
    entry_events = [e for e in events if e.event_type == "ENTRY"]
    assert len(entry_events) == 0   # No new entry


def test_re_entry_detection(tracker, zone_map):
    t0 = datetime(2026, 4, 10, 12, 0, 0)
    # Person enters
    tracker.update([(100, 200)], t0, zone_map)

    # Person exits (by absence — advance time by 3 seconds)
    t1 = datetime(2026, 4, 10, 12, 0, 3)
    exit_events = tracker.update([], t1, zone_map)
    assert any(e.event_type == "EXIT" for e in exit_events)

    # Person re-enters within 10 minutes
    t2 = datetime(2026, 4, 10, 12, 5, 0)
    re_events = tracker.update([(100, 200)], t2, zone_map)
    re_entry_events = [e for e in re_events if e.event_type == "REENTRY"]
    assert len(re_entry_events) == 1


def test_zone_transitions(tracker, zone_map):
    """Test movement from ENTRY to FLOOR zone"""
    t0 = datetime(2026, 4, 10, 12, 0, 0)
    # Entry zone (x=100 is in ENTRY zone 0-150)
    events = tracker.update([(100, 200)], t0, zone_map)
    entry_events = [e for e in events if e.event_type == "ENTRY"]
    assert len(entry_events) == 1
    visitor_id = entry_events[0].visitor_id

    # Move to floor zone within matching distance
    # Move from x=100 to x=145 (still in ENTRY 0-150), then next frame to x=155 (in FLOOR 150-960)
    t1 = datetime(2026, 4, 10, 12, 0, 1)
    events = tracker.update([(145, 200)], t1, zone_map)  # Move within ENTRY zone still
    zone_events = [e for e in events if e.event_type == "ZONE_EXIT"]
    assert len(zone_events) == 0  # Still in same zone

    # Now move to FLOOR
    t2 = datetime(2026, 4, 10, 12, 0, 2)
    events = tracker.update([(155, 200)], t2, zone_map)  # Move to FLOOR (150-960)
    zone_enter = [e for e in events if e.event_type == "ZONE_ENTER"]
    assert len(zone_enter) > 0
    assert zone_enter[0].zone_id == "FLOOR"


def test_staff_detection_before_cutoff(tracker, zone_map):
    """Track before 10:30 = staff."""
    early = datetime(2026, 4, 10, 9, 0, 0)
    events = tracker.update([(100, 200)], early, zone_map)
    entry = next(e for e in events if e.event_type == "ENTRY")
    assert entry.is_staff is True


def test_customer_detection_after_cutoff(tracker, zone_map):
    """Track after 10:30 = customer."""
    later = datetime(2026, 4, 10, 11, 0, 0)
    events = tracker.update([(100, 200)], later, zone_map)
    entry = next(e for e in events if e.event_type == "ENTRY")
    assert entry.is_staff is False


def test_group_entry_separate_tracks(tracker, zone_map):
    """Two distinct centroids = two separate tracks."""
    frame_time = datetime(2026, 4, 10, 13, 0, 0)
    events = tracker.update([(50, 100), (200, 300)], frame_time, zone_map)
    entry_events = [e for e in events if e.event_type == "ENTRY"]
    assert len(entry_events) == 2
    visitor_ids = {e.visitor_id for e in entry_events}
    assert len(visitor_ids) == 2   # Different IDs


def test_exit_records_dwell_time(tracker, zone_map):
    t_enter = datetime(2026, 4, 10, 14, 0, 0)
    tracker.update([(100, 200)], t_enter, zone_map)

    # Advance 3 seconds (missing)
    t_exit = datetime(2026, 4, 10, 14, 0, 3)
    events = tracker.update([], t_exit, zone_map)
    exit_events = [e for e in events if e.event_type == "EXIT"]
    assert len(exit_events) == 1
    assert exit_events[0].dwell_ms is not None
    assert exit_events[0].dwell_ms >= 0


def test_centroid_matching_radius(tracker, zone_map):
    """Centroids > 50px apart = different people."""
    frame_time = datetime(2026, 4, 10, 15, 0, 0)
    tracker.update([(100, 100)], frame_time, zone_map)

    frame_time2 = datetime(2026, 4, 10, 15, 0, 1)
    events = tracker.update([(200, 200)], frame_time2, zone_map)   # 141px away
    # Should register as new entry (too far to match)
    # First track exits + new entry
    entries = [e for e in events if e.event_type == "ENTRY"]
    assert len(entries) >= 1
