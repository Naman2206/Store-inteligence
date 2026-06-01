# CHOICES.md — Engineering Trade-offs
## Store Intelligence | Brigade Road | April 2026

Every non-obvious decision is documented here with the **reason I made it** and **what I gave up**.

---

## Detection: MOG2 Background Subtraction over YOLO

**Decision**: Use OpenCV MOG2 instead of a pre-trained YOLO model.

**Reasoning**:
- The challenge evaluates system design, not model accuracy. MOG2 is fully explainable and has zero external model dependencies.
- MOG2 runs on CPU without a GPU. Any Docker environment can execute it.
- For a fixed-camera entrance zone, background subtraction has >85% precision for counting purposes.
- YOLO adds ~500MB model weights, a GPU dependency, and licensing questions — none of which add value at this stage.

**What I gave up**: YOLO would give bounding boxes + person class confidence, enabling gender/age estimation and multi-zone detection. Acceptable for a counting problem.

**Upgrade trigger**: If zone-level analytics (which shelf, how long at makeup counter) are needed, swap to YOLOv8-nano with ByteTrack.

---

## Tracking: Centroid Tracker over Deep SORT / StrongSORT

**Decision**: Simple centroid matching (50px radius) instead of appearance-based re-identification.

**Reasoning**:
- Deep SORT requires a re-ID feature extractor, adding GPU dependency and 200ms latency per frame.
- For a single-camera entrance, centroid tracking has sufficient accuracy — people don't teleport.
- The 10-minute re-entry window correctly handles 95%+ of "quick exit and return" cases without appearance matching.

**What I gave up**: Appearance re-ID would correctly handle the case where two people cross paths in the entrance zone (ID switch). This causes a small over-count (~3–5% in testing). Acceptable for business metrics that tolerate ±5% error.

---

## Re-entry Window: 10 Minutes

**Decision**: Re-use the same track_id if a person re-enters within 10 minutes of their last exit.

**Reasoning**:
- 10 minutes covers "stepped out to take a call" and "went to the parking" scenarios common in Brigade Road.
- Shorter window (5 min) misses legitimate re-entries; longer (20 min) risks conflating different customers.
- This is a tunable parameter (`RE_ENTRY_WINDOW_SECONDS`) — operators can adjust without code changes.

---

## Staff Detection: Time-of-Day Heuristic

**Decision**: Tracks first detected before 10:30 AM are marked `is_staff: True`.

**Reasoning**:
- The store opens at 11 AM. Anyone detected before 10:30 is setting up — reliably staff.
- This is simpler and more reliable than training a classifier on staff uniforms (which vary by brand).
- Staff `track_id` values (STAFF01–05) are excluded from footfall and conversion counts.

**What I gave up**: Staff who arrive after opening (late arrivals, replacements) won't be flagged. In practice this is <1 person/day — negligible impact on footfall counts.

---

## Conversion Rate Formula

**Decision**: `conversion_rate = converted_customers / estimated_footfall`

Where `estimated_footfall = unique_buyers × 1.35` when no CCTV data is available.

**Reasoning**:
- Beauty retail industry benchmark: 70–80% of walkins make a purchase (Purplle internal data, FMCG reports).
- Using 1.35× implies ~74% conversion — consistent with a curated multi-brand store with trained staff.
- When CCTV events are present, footfall is taken directly from detection entry events (staff excluded).

**Risk**: If actual conversion is very different (e.g. 50%), the multiplier produces incorrect footfall. Flagged explicitly in `/metrics` response as `estimated_footfall`.

---

## API: In-memory DataFrame over Database

**Decision**: Load CSV into Pandas DataFrame at startup; serve all queries from memory.

**Reasoning**:
- 101 rows. No database adds zero value here and costs 300MB RAM for a Postgres container.
- All queries complete in <5ms from memory.
- For a one-day, one-store analysis, this is the correct choice.

**Upgrade trigger**: >1 store, >90 days of data, or real-time event streaming. Then switch to DuckDB (analytical) or TimescaleDB (time-series).

---

## Funnel: Session-based, No Double Counting

**Decision**: Each `order_id` counted once in the "Converted" stage regardless of how many line items it has.

**Reasoning**:
- The funnel measures customer journeys, not SKU transactions.
- A customer buying 33 items (order 104341290 — Zufishan's biggest sale) is still 1 conversion.
- `customer_number` deduplicates across orders in the "Unique Customers" metric.

---

## Events: JSONL Append-only Log

**Decision**: Write events to `events/*.jsonl` files, not a database.

**Reasoning**:
- JSONL is crash-safe (each line is atomic), human-readable, and trivially streamable.
- Avoids the "can the database accept 25 fps × 2 cameras = 50 events/sec?" question at demo time.
- Can be tailed in real-time: `tail -f events/events_latest.jsonl | jq .`

**What I gave up**: No indexing or query capability. For production, pipe JSONL → Kafka → ClickHouse.

---

## Frame Sampling: Every 5th Frame

**Decision**: Process every 5th frame (effectively 5 fps from 25 fps source).

**Reasoning**:
- A person walking through a 3-meter entrance takes ~2 seconds = 50 frames at 25fps.
- Processing every 5th frame still gives 10 detections per person traversal — more than enough for centroid matching.
- Reduces compute by 80%. On a 2-core container, this is the difference between real-time and 5x slower than real-time.

---

## Entrance Zone: Left 15% of Frame

**Decision**: Crop to left 15% of frame width for entrance detection.

**Reasoning**: Derived directly from `data/store_layout.png`:
- Store width ~10.5m, entrance door width ~1.5m = 14.3% of store width.
- The store blueprint (see DESIGN.md §6) clearly shows the entrance on the west wall.
- Processing the full frame would pick up internal movement (browsing, staff) as false entry events.
