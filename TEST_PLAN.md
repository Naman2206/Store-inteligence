# TEST_PLAN.md — Store Intelligence Submission Test Framework

**Purpose:** Align manual and automated testing with the UpGrad Placements (April 2026) evaluation rubric so a reviewer can validate the system in ~10 minutes and you can self-score before submission.

**Related docs:** `DESIGN.md`, `CHOICES.md`, `README.md`

---

## 1. Evaluation mapping (score → tests)

| Rubric area | Marks | What “Strong” means | Primary test layers |
|-------------|-------|---------------------|---------------------|
| Detection pipeline | 30 | Entry/exit near ground truth; re-entry, staff, groups; structured events | L2 pipeline, L3 E2E video, L4 manual ground truth |
| API & business logic | 35 | Correct `/metrics`, `/funnel`; session-based funnel; meaningful anomalies | L1 API contract, L3 integration, integrity |
| Production readiness | 20 | `docker compose up`; logs/metrics; tests cover edge cases | L0 acceptance gate, L5 observability |
| Engineering thinking | 15 | Clear `DESIGN.md` + `CHOICES.md` | L6 documentation checklist |

**Integrity cap (50 max):** Outputs must change with different inputs (video, CSV, events). No static/hardcoded API payloads independent of data.

---

## 2. Test layers (framework)

```
L0 Acceptance gate     → Must pass or submission rejected
L1 API smoke           → Reviewer minutes 0–2
L2 Detection unit      → Pipeline logic in isolation
L3 Integration         → events/*.jsonl → API consistency
L4 Ground-truth video  → Count accuracy vs human label
L5 Production          → Docker, health, logs, crash-free run
L6 Documentation       → DESIGN + CHOICES reviewer checklist
L7 Integrity           → Input variation / anti-hardcoding
```

Run order for self-check before submit: **L0 → L1 → L2 → L3 → L7 → L4 → L5 → L6**.

---

## 3. L0 — Acceptance gate (mandatory)

| ID | Check | How to verify | Pass criteria |
|----|-------|---------------|---------------|
| A0.1 | One-command startup | `docker compose up` (fresh clone, no manual steps) | All services start; no crash loop |
| A0.2 | API reachable | `curl -s http://localhost:8000/health` | HTTP 200, `"status": "ok"`, `rows_loaded > 0` |
| A0.3 | Metrics endpoint | `curl -s http://localhost:8000/metrics` | HTTP 200, valid JSON, non-empty `summary` |
| A0.4 | Events produced | `ls events/*.jsonl` after detection runs | At least one `.jsonl` with `entry` lines |
| A0.5 | Documentation | Open `DESIGN.md`, `CHOICES.md` at repo root | Non-trivial content; architecture + trade-offs present |

**Stability (pre-scoring):** System must not crash during a 15-minute idle run with API under light load (`curl` loop on `/health`, `/metrics`, `/funnel` every 30s).

---

## 4. L1 — API smoke (reviewer ~2 min)

Base URL: `http://localhost:8000`

| ID | Endpoint | Assertion |
|----|----------|-----------|
| S1.1 | `GET /health` | 200; `status == "ok"` |
| S1.2 | `GET /metrics` | 200; keys: `summary`, `by_department`, `by_hour`, `by_salesperson`, `top_brands` |
| S1.3 | `GET /metrics/summary` | `total_gmv > 0`, `total_nmv <= total_gmv`, `0 < conversion_rate_pct <= 100` |
| S1.4 | `GET /funnel` | 200; `stages` monotonic non-increasing counts; `overall_conversion_pct` in (0, 100] |
| S1.5 | `GET /anomalies` | `anomalies[]` each has `type`, `severity` ∈ {low, medium, high}, `description` |
| S1.6 | `GET /events` | `events[]` with `event_id`, `event_type`, `track_id`, `timestamp` |
| S1.7 | `GET /events/summary` | `entries >= re_entries` |

**Automated:** `pytest tests/test_api.py -v` (see §9).

---

## 5. L2 — Detection pipeline unit tests (30 marks — core)

Target: `detection/pipeline.py` (`PersonTracker`, event types).

| ID | Scenario | Rubric link | Expected behavior |
|----|----------|-------------|-------------------|
| D2.1 | Single entry | Entry/exit | One `entry`, new `track_id` |
| D2.2 | Centroid match | Occlusion / continuity | Same person, no duplicate `entry` |
| D2.3 | Re-entry | Re-entry | `exit` then `re_entry` within window (10 min) |
| D2.4 | Staff before cutoff | Staff | `is_staff: true` before configured time |
| D2.5 | Customer after cutoff | Staff | `is_staff: false` after cutoff |
| D2.6 | Group entry | Group | N centroids → N distinct `track_id`s |
| D2.7 | Exit + dwell | Edge cases | `exit` with `dwell_minutes >= 0` |
| D2.8 | Far centroid | Occlusion / split | Centroids > match radius → new track or exit+entry |

**Automated:** `pytest tests/test_detection.py -v`

---

## 6. L3 — Integration (events ↔ API)

| ID | Scenario | Steps | Pass criteria |
|----|----------|-------|---------------|
| I3.1 | Footfall drives conversion | Run detection → note `entries` from `/events/summary` → `GET /metrics/summary` | `estimated_footfall` aligns with entry count when events exist |
| I3.2 | Funnel footfall stage | Same as above → `GET /funnel` | First stage `Footfall` ≈ entry count (not only CSV heuristic) |
| I3.3 | No double counting | Compare `/funnel` `Converted` vs `/metrics/summary` `unique_customers` | `Converted <= unique_customers + tolerance` |
| I3.4 | Event schema | Sample 20 lines from `events/*.jsonl` | Required fields present; types consistent |
| I3.5 | Filter API | `GET /events?event_type=entry` | All returned events are `entry` |

### Event schema contract

Each JSONL record should include:

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | string | Unique per event |
| `event_type` | enum | `entry`, `exit`, `re_entry`, `dwell` |
| `track_id` | string | Stable per visit session |
| `timestamp` | ISO-8601 | Parseable |
| `zone` | string | e.g. `entrance` |
| `confidence` | float | 0–1 |
| `is_staff` | bool | Staff filtering |
| `dwell_minutes` | float \| null | Set on `exit` |

**Gap to fix before submit:** Duplicate `event_id` values in some generated files weaken “structured, complete, consistent” — validate uniqueness in L3.4.

---

## 7. L4 — Ground-truth video validation (detection accuracy)

Use a **short clip (30–120 s)** with a human-labeled ground truth sheet.

| ID | Clip type | Label | Compare |
|----|-----------|-------|---------|
| V4.1 | Single person in/out | entries=1, exits=1 | `/events/summary` ± margin |
| V4.2 | Re-entry | 1 person, 2 entries (1 re_entry) | `re_entries >= 1` |
| V4.3 | Two people together | entries=2 | distinct `track_id`s |
| V4.4 | Staff hour | entries before 10:30 | `is_staff: true` on those tracks |
| V4.5 | Busy entrance | entries=N (manual count) | error margin ≤ 15–20% (document assumption in `CHOICES.md`) |

**Ground truth template:**

| clip_id | duration_s | manual_entries | manual_exits | manual_re_entries | notes |
|---------|------------|----------------|--------------|-------------------|-------|
| clip_01 | 60 | | | | |

**Pass:** Document margin and known failure modes (occlusion, overlapping silhouettes) in `CHOICES.md`.

---

## 8. L5 — Production readiness

| ID | Area | Test |
|----|------|------|
| P5.1 | Deployment | Fresh machine: clone → `docker compose up` only |
| P5.2 | Healthcheck | API container healthcheck passes |
| P5.3 | Dashboard | http://localhost:3000 loads; calls API |
| P5.4 | Logging | Detection + API logs show startup, row count, event writes |
| P5.5 | Automated tests | `pytest tests/ -v` green in CI or locally documented |
| P5.6 | Failure recovery | Stop detection container; API still serves metrics from CSV |

---

## 9. L7 — Integrity (anti–hardcoding)

| ID | Test | Pass |
|----|------|------|
| N7.1 | Empty events dir | Rename `events/` → restart API → metrics/funnel use fallback; values differ from “with events” run |
| N7.2 | Alter CSV | Change row count or GMV in copy → `/metrics/summary` `total_gmv` changes |
| N7.3 | New video run | Second detection run appends/new jsonl → `/events/summary` counts change |
| N7.4 | Cross-check | `conversion_rate_pct` computable from `unique_customers` and `estimated_footfall` in response |

---

## 10. L6 — Documentation reviewer checklist (~2 min)

| ID | File | Reviewer question | Strong signal |
|----|------|-------------------|---------------|
| DOC1 | `DESIGN.md` | Can I draw the pipeline from this? | Diagram + interfaces |
| DOC2 | `DESIGN.md` | Edge cases listed with handling? | Table matches L2/L4 tests |
| DOC3 | `CHOICES.md` | Why MOG2 vs YOLO? Why centroid vs DeepSORT? | Explicit trade-offs |
| DOC4 | `CHOICES.md` | Footfall / funnel assumptions? | Numbers tied to business metric |
| DOC5 | `TEST_PLAN.md` | How did you verify? | This file + pytest |

**Note:** Rubric expects `DESIGN.md` and `CHOICES.md` at repo root (you have both root and `docs/` copies — keep them in sync).

---

## 11. 10-minute reviewer simulation (rehearsal script)

| Minute | Action | Commands / artifacts |
|--------|--------|----------------------|
| 0–2 | Start + API | `docker compose up -d` → `curl /health` `/metrics` |
| 2–4 | Events | `tail -5 events/*.jsonl` → `curl /events/summary` |
| 4–7 | API logic | `curl /funnel` `/anomalies` — check funnel order + conversion |
| 7–9 | Docs | Skim `DESIGN.md`, `CHOICES.md` |
| 9–10 | Self-score | Use §12 rubric |

---

## 12. Self-scoring rubric (copy per area)

Rate each: **Weak (0–33%)** | **Moderate (34–66%)** | **Strong (67–100%)** of section marks.

### Detection (30)
- [ ] Entry/exit within reasonable margin on sample video
- [ ] Re-entry, staff, group scenarios covered by tests or demo clip
- [ ] Events JSONL complete and consistent schema

### API (35)
- [ ] All endpoints correct and consistent with data
- [ ] Funnel session-based; no obvious double count
- [ ] Anomalies plausible (spike/outlier/concentration)

### Production (20)
- [ ] Docker one-command
- [ ] Logs informative
- [ ] pytest covers L1 + L2 scenarios

### Thinking (15)
- [ ] DESIGN + CHOICES specific to this store, not generic

**Target:** 85+ strong candidate | 70–85 interview-ready.

---

## 13. Automated test commands

```bash
# API + detection unit tests
pip install pytest httpx pandas fastapi
pytest tests/ -v

# Acceptance curl script (API must be running)
./scripts/smoke_test.sh   # optional: create from §4 table
```

### Existing coverage (`tests/`)

| File | Covers |
|------|--------|
| `test_api.py` | L1 endpoints, funnel monotonicity, anomaly shape, events filter |
| `test_detection.py` | L2 scenarios D2.1–D2.8 |

### Recommended additions (pre-submit)

1. **E2E:** Docker compose health wait + curl integration test.
2. **Schema:** Assert unique `event_id` in jsonl loader test.
3. **Integrity:** Test metrics change when `EVENTS_OUTPUT` empty vs populated.
4. **CI:** GitHub Action running `pytest` on push.

---

## 14. Edge-case test matrix (tie-breakers)

| Edge case | Detection test | API test | Demo for reviewer |
|-----------|----------------|----------|-------------------|
| Re-entry | D2.3, V4.2 | `re_entries` in summary | Short clip or log excerpt |
| Staff | D2.4–D2.5, V4.4 | Filter staff in funnel footfall (if implemented) | Events with `is_staff` |
| Group entry | D2.6, V4.3 | Footfall += N | Two people entering together |
| Occlusion | D2.2, D2.8 | — | Note 5-frame gap in DESIGN |
| Empty store | No contours | Zero/low entries | Optional clip |

---

## 15. Pre-submission checklist

- [ ] L0 all pass on clean machine
- [ ] 10-minute rehearsal completed once
- [ ] `pytest tests/ -v` green
- [ ] `DESIGN.md` / `CHOICES.md` at root match `docs/` versions
- [ ] Sample `events/*.jsonl` committed or generated on first `docker compose up`
- [ ] README “Running Tests” section matches actual commands
- [ ] Integrity tests N7.1–N7.3 documented with observed outputs
- [ ] Known limitations listed in `CHOICES.md` (accuracy margin, heuristic funnel stages)

---

*Version: 1.0 — aligned to UpGrad Store Intelligence Challenge evaluation framework (April 2026).*
