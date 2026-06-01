"""
tests/test_detection.py — Unit tests for detection pipeline components
"""
import pytest
from datetime import datetime
from detection.pipeline import PersonTracker, TrackEvent


@pytest.fixture
def tracker():
    return PersonTracker()


def test_new_entry_creates_track(tracker):
    frame_time = datetime(2026, 4, 10, 12, 0, 0)
    events = tracker.update([(100, 200)], frame_time, is_entrance_zone=True)
    entry_events = [e for e in events if e.event_type == "entry"]
    assert len(entry_events) == 1
    assert entry_events[0].track_id.startswith("T")


def test_matched_centroid_no_new_event(tracker):
    frame_time = datetime(2026, 4, 10, 12, 0, 0)
    tracker.update([(100, 200)], frame_time, True)

    frame_time2 = datetime(2026, 4, 10, 12, 0, 1)
    events = tracker.update([(105, 198)], frame_time2, True)   # close centroid = same person
    entry_events = [e for e in events if e.event_type == "entry"]
    assert len(entry_events) == 0   # No new entry


def test_re_entry_detection(tracker):
    t0 = datetime(2026, 4, 10, 12, 0, 0)
    # Person enters
    tracker.update([(100, 200)], t0, True)

    # Person exits (by absence — advance time by 3 seconds)
    t1 = datetime(2026, 4, 10, 12, 0, 3)
    exit_events = tracker.update([], t1, True)
    assert any(e.event_type == "exit" for e in exit_events)

    # Person re-enters within 10 minutes
    t2 = datetime(2026, 4, 10, 12, 5, 0)
    re_events = tracker.update([(100, 200)], t2, True)
    re_entry_events = [e for e in re_events if e.event_type == "re_entry"]
    assert len(re_entry_events) == 1


def test_staff_detection_before_cutoff(tracker):
    """Track before 10:30 = staff."""
    early = datetime(2026, 4, 10, 9, 0, 0)
    events = tracker.update([(100, 200)], early, True)
    entry = next(e for e in events if e.event_type == "entry")
    assert entry.is_staff is True


def test_customer_detection_after_cutoff(tracker):
    """Track after 10:30 = customer."""
    later = datetime(2026, 4, 10, 11, 0, 0)
    events = tracker.update([(100, 200)], later, True)
    entry = next(e for e in events if e.event_type == "entry")
    assert entry.is_staff is False


def test_group_entry_separate_tracks(tracker):
    """Two distinct centroids = two separate tracks."""
    frame_time = datetime(2026, 4, 10, 13, 0, 0)
    events = tracker.update([(50, 100), (200, 300)], frame_time, True)
    entry_events = [e for e in events if e.event_type == "entry"]
    assert len(entry_events) == 2
    track_ids = {e.track_id for e in entry_events}
    assert len(track_ids) == 2   # Different IDs


def test_exit_records_dwell_time(tracker):
    t_enter = datetime(2026, 4, 10, 14, 0, 0)
    tracker.update([(100, 200)], t_enter, True)

    # Advance 3 seconds (missing)
    t_exit = datetime(2026, 4, 10, 14, 0, 3)
    events = tracker.update([], t_exit, True)
    exit_events = [e for e in events if e.event_type == "exit"]
    assert len(exit_events) == 1
    assert exit_events[0].dwell_minutes is not None
    assert exit_events[0].dwell_minutes >= 0


def test_centroid_matching_radius(tracker):
    """Centroids > 50px apart = different people."""
    frame_time = datetime(2026, 4, 10, 15, 0, 0)
    tracker.update([(100, 100)], frame_time, True)

    frame_time2 = datetime(2026, 4, 10, 15, 0, 1)
    events = tracker.update([(200, 200)], frame_time2, True)   # 141px away
    # Should register as new entry (too far to match)
    # First track exits + new entry
    entries = [e for e in events if e.event_type == "entry"]
    assert len(entries) >= 1
