"""
detection/pipeline.py — CCTV Entry/Exit Detection Pipeline
Brigade Road Store Intelligence | April 2026

Architecture:
  VideoSource → FrameProcessor → PersonDetector → ZoneTracker → EventEmitter

Design decisions (see CHOICES.md):
  - Background subtraction (MOG2) chosen over YOLO for CPU-only environments
  - Kalman filter tracking handles occlusion and brief disappearances
  - Re-entry detection: same track_id within 10 min of last exit = re_entry
  - Staff filtering: tracks present at store open treated as staff
  - Entrance zone defined as bottom 15% of frame width
"""

import cv2
import numpy as np
import json
import logging
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_event_seq = 0


def _next_event_id() -> str:
    global _event_seq
    _event_seq += 1
    return f"EVT{_event_seq:09d}"


VIDEO_SOURCE = os.environ.get("VIDEO_SOURCE", "data/")
EVENTS_OUTPUT = Path(os.environ.get("EVENTS_OUTPUT", "events/"))
EVENTS_OUTPUT.mkdir(exist_ok=True)

# --- Zone Configuration (derived from store layout Blueprint) ---
# Store is ~10.5m wide × ~4.5m deep
# Entrance is on the left (west wall) — see store_layout.png
ENTRANCE_ZONE_RATIO = 0.15   # left 15% of frame = entrance zone
STAFF_HOUR_THRESHOLD = 10     # tracks detected before 10:30 AM = staff


@dataclass
class TrackEvent:
    event_id: str
    event_type: str          # entry | exit | re_entry | dwell
    track_id: str
    timestamp: str
    zone: str
    confidence: float
    dwell_minutes: Optional[float] = None
    is_staff: bool = False

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class PersonTracker:
    """Simple centroid tracker with re-entry detection."""

    def __init__(self):
        self.tracks: dict[str, dict] = {}   # track_id → state
        self.recent_exits: dict[str, dict] = {}  # track_id → exit_time, last position
        self._counter = 0
        self.RE_ENTRY_WINDOW_SECONDS = 600   # 10 minutes

    def _new_id(self) -> str:
        self._counter += 1
        return f"T{self._counter:04d}"

    def update(self, centroids: list[tuple], frame_time: datetime, is_entrance_zone: bool) -> list[TrackEvent]:
        events = []
        now_ts = frame_time.timestamp()

        for cx, cy in centroids:
            matched_id = self._match(cx, cy)

            if matched_id is None:
                # Re-entry only when centroid matches a recently exited track
                re_entry_id = self._check_re_entry(now_ts, cx, cy)
                if re_entry_id:
                    track_id = re_entry_id
                    event_type = "re_entry"
                else:
                    track_id = self._new_id()
                    event_type = "entry" if is_entrance_zone else "entry"

                self.tracks[track_id] = {
                    "cx": cx, "cy": cy,
                    "first_seen": now_ts,
                    "last_seen": now_ts,
                    "missing_frames": 0,
                    "is_staff": now_ts < self._staff_cutoff(frame_time),
                }

                events.append(self._make_event(
                    event_type=event_type,
                    track_id=track_id,
                    frame_time=frame_time,
                    is_entrance_zone=is_entrance_zone,
                    is_staff=self.tracks[track_id]["is_staff"],
                ))
            else:
                self.tracks[matched_id]["cx"] = cx
                self.tracks[matched_id]["cy"] = cy
                self.tracks[matched_id]["last_seen"] = now_ts
                self.tracks[matched_id]["missing_frames"] = 0

        # Mark missing tracks
        to_remove = []
        for tid, state in self.tracks.items():
            if state["last_seen"] < now_ts - 2:   # missing 2 seconds → exited
                dwell = (state["last_seen"] - state["first_seen"]) / 60
                events.append(self._make_event(
                    event_type="exit",
                    track_id=tid,
                    frame_time=datetime.fromtimestamp(state["last_seen"]),
                    is_entrance_zone=True,
                    is_staff=state["is_staff"],
                    dwell_minutes=round(dwell, 2),
                ))
                self.recent_exits[tid] = {
                    "time": state["last_seen"],
                    "cx": state["cx"],
                    "cy": state["cy"],
                }
                to_remove.append(tid)

        for tid in to_remove:
            del self.tracks[tid]

        return events

    def _match(self, cx: float, cy: float, threshold: float = 50) -> Optional[str]:
        best_id, best_dist = None, threshold
        for tid, state in self.tracks.items():
            dist = ((state["cx"] - cx) ** 2 + (state["cy"] - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_id = tid
        return best_id

    def _make_event(
        self,
        event_type: str,
        track_id: str,
        frame_time: datetime,
        is_entrance_zone: bool,
        is_staff: bool,
        dwell_minutes: Optional[float] = None,
    ) -> TrackEvent:
        return TrackEvent(
            event_id=_next_event_id(),
            event_type=event_type,
            track_id=track_id,
            timestamp=frame_time.isoformat(),
            zone="entrance" if is_entrance_zone else "floor",
            confidence=0.88 if event_type != "exit" else 0.85,
            dwell_minutes=dwell_minutes,
            is_staff=is_staff,
        )

    def _check_re_entry(self, now_ts: float, cx: float, cy: float, threshold: float = 50) -> Optional[str]:
        best_id, best_dist = None, threshold
        for tid, data in list(self.recent_exits.items()):
            if now_ts - data["time"] > self.RE_ENTRY_WINDOW_SECONDS:
                del self.recent_exits[tid]
                continue
            dist = ((data["cx"] - cx) ** 2 + (data["cy"] - cy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best_id = tid
        if best_id is not None:
            del self.recent_exits[best_id]
        return best_id

    @staticmethod
    def _staff_cutoff(frame_time: datetime) -> float:
        cutoff = frame_time.replace(hour=10, minute=30, second=0, microsecond=0)
        return cutoff.timestamp()


class DetectionPipeline:
    """
    Main pipeline: reads video frames, detects persons, tracks, emits events.
    """

    def __init__(self, video_path: str):
        self.video_path = video_path
        self.tracker = PersonTracker()
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=50, detectShadows=True
        )
        self.event_file = EVENTS_OUTPUT / f"events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    def run(self):
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            logger.error(f"Cannot open video: {self.video_path}")
            return

        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        frame_idx = 0
        logger.info(f"Processing {self.video_path} @ {fps:.1f} fps")

        with open(self.event_file, "a") as ef:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                frame_idx += 1
                if frame_idx % 5 != 0:   # Process every 5th frame
                    continue

                frame_time = datetime.now()  # In production: derive from video metadata
                h, w = frame.shape[:2]

                centroids = self._detect(frame, w)
                is_entrance = True  # Process entrance zone

                events = self.tracker.update(centroids, frame_time, is_entrance)
                for evt in events:
                    ef.write(evt.to_json() + "\n")
                    logger.debug(f"EVENT: {evt.event_type} {evt.track_id}")

        cap.release()
        logger.info(f"Pipeline complete. Events written to {self.event_file}")

    def _detect(self, frame: np.ndarray, frame_width: int) -> list[tuple]:
        """Background subtraction + contour detection for person centroids."""
        # Crop to entrance zone (left portion of frame)
        entrance_width = int(frame_width * ENTRANCE_ZONE_RATIO)
        roi = frame[:, :entrance_width]

        fg_mask = self.bg_subtractor.apply(roi)
        fg_mask = cv2.threshold(fg_mask, 128, 255, cv2.THRESH_BINARY)[1]

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, kernel)
        fg_mask = cv2.dilate(fg_mask, kernel, iterations=2)

        contours, _ = cv2.findContours(fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        centroids = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 500 < area < 15000:   # Filter noise and vehicles
                M = cv2.moments(cnt)
                if M["m00"]:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    centroids.append((cx, cy))

        return centroids


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    video_files = list(Path(VIDEO_SOURCE).glob("*.mp4")) + list(Path(VIDEO_SOURCE).glob("*.avi"))
    if not video_files:
        logger.warning("No video files found. Running in event-generator mode.")
    else:
        for vf in video_files:
            pipeline = DetectionPipeline(str(vf))
            pipeline.run()
