# DESIGN.md — Store Intelligence System
## Brigade Road, Bangalore | April 2026

---

## 1. Problem Decomposition

The challenge is to take raw CCTV footage from a single store and produce **business-meaningful metrics**:
store conversion rate, customer dwell time, department-level footfall, and anomaly detection.

This breaks into three independent sub-problems:

```
CCTV Video ──► Detection Pipeline ──► Structured Events ──► Business API ──► Dashboard
```

Each layer has a **clean interface** so any component can be swapped without breaking the others.

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    docker-compose.yml                           │
│                                                                 │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────┐  │
│  │  detection/      │   │  api/            │   │  dashboard │  │
│  │  pipeline.py     │──►│  FastAPI         │──►│  React     │  │
│  │                  │   │  /metrics        │   │  Port 3000 │  │
│  │  MOG2 BG Sub     │   │  /funnel         │   │            │  │
│  │  Centroid Track  │   │  /anomalies      │   └────────────┘  │
│  │  Re-entry logic  │   │  /events         │                   │
│  └──────────────────┘   └──────────────────┘                   │
│         │                       ▲                              │
│         ▼                       │                              │
│    events/*.jsonl ──────────────┘                              │
│    data/sales_10_april_2026.csv                                │
└─────────────────────────────────────────────────────────────────┘
```

### Components

| Component | Responsibility | Tech |
|-----------|---------------|------|
| `detection/pipeline.py` | Frame-level person detection, tracking, event emission | OpenCV MOG2, centroid tracker |
| `api/main.py` | REST API serving business metrics | FastAPI, Pandas |
| `api/routers/metrics.py` | Core KPIs: GMV, NMV, conversion, basket size | Pandas aggregations |
| `api/routers/funnel.py` | Session-based customer funnel | Business logic layer |
| `api/routers/anomalies.py` | Statistical anomaly detection | Z-score, IQR |
| `api/routers/events.py` | CCTV event log (JSONL) | File-based streaming |

---

## 3. Detection Pipeline Design

### Frame Processing
1. **Frame sampling**: Process every 5th frame (5 fps effective). Reduces CPU by 80% with negligible accuracy loss for person counting.
2. **Background subtraction**: MOG2 with shadow detection. Handles the store's fixed lighting well.
3. **Entrance zone crop**: Only the entrance-side 15% of the frame width is processed (derived from store blueprint — entrance is on west wall).
4. **Contour filtering**: Contours between 500–15,000 px² are treated as persons (filters noise and wall fixtures).

### Person Tracking
- **Centroid tracker** with 50px matching radius
- **Kalman filter** optional upgrade path (see CHOICES.md)
- **Exit detection**: Track missing for >2 consecutive seconds = exit event

### Edge Cases Handled

| Edge Case | Handling |
|-----------|---------|
| Re-entry | Track ID reused within 10-minute window of last exit |
| Staff movement | Tracks detected before 10:30 AM marked `is_staff: True` |
| Group entry | Each distinct centroid → separate track_id |
| Occlusion | Missing-frame counter allows 5-frame gap before exit event |
| Shadow detection | MOG2 `detectShadows=True` suppresses shadow contours |

---

## 4. API Design

All endpoints return JSON. No authentication required (internal network assumed).

### `/metrics` (GET)
Returns full store KPIs: GMV, NMV, conversion rate, basket metrics, hourly breakdown, salesperson performance, top brands/SKUs.

### `/funnel` (GET)
Session-based customer funnel from footfall → conversion. No double counting: each `order_id` is counted once. Footfall derived from detection events; falls back to `customers × 1.35` if events unavailable.

### `/anomalies` (GET)
Five anomaly detectors running on every request:
- **Hourly GMV spike**: Z-score > 2
- **Large basket**: IQR × 1.5
- **High discount rate**: > 5%
- **Salesperson concentration**: single rep > 50% GMV
- **Dead hours**: no transactions in trading hours

### `/events` (GET)
Returns structured detection events from JSONL log. Supports filtering by `event_type`.

---

## 5. Data Flow

```
CSV transactions ──► DataLoader ──► In-memory DataFrame
                                         │
                              ┌──────────┼───────────┐
                              ▼          ▼           ▼
                           metrics    funnel     anomalies
```

The CSV is loaded once at startup (`lifespan` context). All queries run against the in-memory DataFrame — no database required for this scale (101 rows).

---

## 6. Store Layout Context

From `data/store_layout.png` (Brigade Road, Bangalore floor plan):

- **Entrance**: Left/west side (sliding glass door)
- **Brands along north wall**: EB Korean, The Face Shop, Good Vibes, DermDoc, Minimalist, Aqualogica, Lakme Skin, Accessories
- **Brands along south wall**: Maybelline, Faces Canada, Lakme, Colorbar+Sugar, Swiss Beauty, Renee NY Bae, Alps Goodness, Streax
- **Centre floor**: F.O.H (Front of House), Makeup Units, Nail Unit, Fragrance
- **Back**: Cash Counter, PMU station, 55" LED panel
- **Exit**: Right/east side

The detection pipeline focuses on the entrance zone. Dwell-time and zone-level analytics would require additional cameras at the makeup unit and brand bays.

---

## 7. Observability

- **Structured logging**: All services use Python `logging` with ISO timestamps
- **Health endpoint**: `/health` returns row count + service status
- **Event log**: Detection events written to `events/*.jsonl` (append-only, crash-safe)
- **Docker health checks**: API container checked every 10s

---

## 8. Scaling Path

Current design handles a single store's daily data in memory. For multi-store / real-time:

1. Replace file-based events with Kafka topic per store
2. Replace in-memory DataFrame with DuckDB for sub-second analytical queries
3. Add Redis cache for `/metrics` (TTL 60s)
4. Swap MOG2 for YOLOv8-nano for multi-zone tracking
