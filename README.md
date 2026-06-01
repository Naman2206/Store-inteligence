# Store Intelligence System
### Brigade Road, Bangalore · 10 April 2026
**UpGrad Placements Challenge — End-to-End Store Analytics Pipeline**

---

## Quick Start

```bash
git clone <repo>
cd store-intelligence
docker compose up
```

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Dashboard**: http://localhost:3000

---

## Architecture

```
CCTV Video ──► detection/pipeline.py ──► events/*.jsonl
                                               │
data/sales_10_april_2026.csv ──────────────────┤
                                               ▼
                                    api/ (FastAPI)
                                    ├── /health
                                    ├── /metrics
                                    ├── /funnel
                                    ├── /anomalies
                                    └── /events
```

See [docs/DESIGN.md](docs/DESIGN.md) for full architecture.
See [docs/CHOICES.md](docs/CHOICES.md) for all trade-off decisions.

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Service health + data status |
| `GET /metrics` | Full KPIs: GMV, NMV, conversion, basket, hourly, by-dept, by-SP, top brands |
| `GET /metrics/summary` | Core metrics only |
| `GET /metrics/hourly` | Hourly breakdown |
| `GET /funnel` | Session-based customer funnel |
| `GET /anomalies` | Detected anomalies (spike, outlier, concentration) |
| `GET /events` | CCTV detection events |
| `GET /events/summary` | Entry/exit/re-entry counts |

---

## Key Metrics (10 Apr 2026)

| Metric | Value |
|--------|-------|
| GMV | ₹44,920 |
| NMV | ₹34,832 |
| Orders | 24 |
| Unique Customers | 21 |
| Avg Basket | ₹1,872 |
| Conversion Rate | ~75% |
| Peak Hour | 19:00 (₹19,237 GMV) |
| Top Brand | Faces Canada (₹20,933) |
| Top Category | Makeup (64% GMV share) |

---

## Running Tests

```bash
pip install -r requirements.test.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/ -v
./scripts/smoke_test.sh   # requires API on :8000
```

See [TEST_PLAN.md](TEST_PLAN.md) for the full evaluation-aligned test framework and [TEST_RESULTS.md](TEST_RESULTS.md) for the latest execution report.

---

## Store Layout

The store layout (`data/store_layout.png`) is Brigade Road, Bangalore:
- **Entrance**: West wall (left side)
- **North brands**: EB Korean, The Face Shop, Good Vibes, DermDoc, Minimalist, Aqualogica, Lakme Skin
- **South brands**: Maybelline, Faces Canada, Lakme, Colorbar+Sugar, Swiss Beauty, Renee NY Bae, Alps Goodness, Streax
- **Centre**: F.O.H, Nail Unit, Fragrance, Makeup Units
- **Back**: Cash Counter, PMU, 55" LED

---

## Project Structure

```
store-intelligence/
├── docker-compose.yml
├── Dockerfile.api
├── Dockerfile.detection
├── requirements.api.txt
├── requirements.detection.txt
├── api/
│   ├── main.py              # FastAPI app + lifespan
│   ├── data_loader.py       # CSV ingestion + cleaning
│   └── routers/
│       ├── health.py
│       ├── metrics.py       # Core KPIs
│       ├── funnel.py        # Customer funnel
│       ├── anomalies.py     # Anomaly detection
│       └── events.py        # CCTV events
├── detection/
│   └── pipeline.py          # MOG2 + centroid tracker
├── docs/
│   ├── DESIGN.md            # System architecture
│   └── CHOICES.md           # Engineering trade-offs
├── tests/
│   ├── test_api.py          # API endpoint tests
│   └── test_detection.py    # Tracker unit tests
└── data/
    ├── sales_10_april_2026.csv
    └── store_layout.png
```
