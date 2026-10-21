# HANDOFF — Bijli-Insight Pakistan

> **Purpose:** Read this at the start of every new session. It captures the full current project state so work can resume immediately without re-reading the codebase.  
> **Update:** Add an entry to "Session Log" at the end of each session describing what changed.

---

## What This Project Is

**HackInsight 2026** submission — national energy intelligence platform for Pakistan's electricity grid.  
Forecasts hourly temperature (cooling demand proxy) for Karachi, Lahore, and Islamabad using LightGBM quantile regression. Provides NEECA/NEPRA-grounded conservation advice via RAG. Polished single-page HTML dashboard served from Vercel; data served by a FastAPI backend running locally.

**Track:** Energy Demand  
**Deadline:** Wed 22 Oct 2026, 11:59 PM PKT

---

## Current Folder Structure

```
Bijli-Insight-Pakistan/
├── index.html                      ← polished single-page HTML dashboard (deploy to Vercel)
├── backend/                        ← all Python backend code
│   ├── __init__.py
│   ├── api.py                      ← FastAPI (6 endpoints: forecast, weather, manifest, status, tariffs, chat)
│   ├── pipeline/
│   │   ├── data_fetcher.py         ← PakistanDataFetcher (all methods implemented)
│   │   ├── generate_manifest.py    ← ManifestBuilder (SHA-256 audit ledger)
│   │   ├── warehouse_pipeline.py   ← DataWarehousePipeline (3-layer DuckDB build)
│   │   └── flow.py                 ← Prefect hourly flow (real inference, real metrics)
│   ├── agents/
│   │   ├── data_quality_agent.py   ← DataQualityAgent (FIX/FILL/FLAG)
│   │   └── insight_rag_agent.py    ← InsightAgentRAG (ChromaDB + DuckDB)
│   └── ml/
│       ├── quantile_model.py       ← QuantileEnergyForecaster (LightGBM pinball q10/q50/q90)
│       └── model_evaluator.py      ← ModelFairnessEvaluator (baseline + group slices)
├── frontend/
│   └── app.py                      ← Streamlit dashboard (kept, but not the demo frontend anymore)
├── data/
│   ├── raw/
│   │   ├── open-meteo-24.85N66.99E7m.csv      ← Karachi weather 2024-2025
│   │   ├── open-meteo-31.53N74.39E220m.csv    ← Lahore weather 2024-2025
│   │   ├── open-meteo-33.64N73.03E527m.csv    ← Islamabad weather 2024-2025
│   │   ├── nepra_tariff_slabs_2024.csv         ← NEPRA 2024 tariff slabs (5 rows)
│   │   └── manifest.csv                        ← SHA-256 audit ledger
│   ├── warehouse.duckdb                        ← cleaned_weather + gold_weather_features
│   ├── pipeline_status.json                    ← real MAE metrics from last flow run
│   ├── quality_log.json                        ← DQA audit trail
│   └── chroma_db/                              ← ChromaDB vector store (RAG)
├── models/
│   ├── lgb_quantile_10.txt
│   ├── lgb_quantile_50.txt
│   └── lgb_quantile_90.txt
├── knowledge_base/
│   ├── neeca_policy_2022.pdf
│   └── neeca_residential_ecbc.pdf
├── tests/                          ← 7/7 passing
├── docs/
│   ├── current_flow.md             ← architecture overview
│   ├── project_flow.md             ← step-by-step file-by-file walkthrough
│   ├── fix.md                      ← what was broken and how it was fixed
│   └── hackathonguide.md           ← original HackInsight guide
├── README.md
├── AI_Use_Log.md                   ← required submission doc
├── Dataset_Declaration.md          ← required submission doc
├── HANDOFF.md                      ← this file
├── Procfile                        ← uvicorn web process (for Render/Heroku if ever needed)
├── Makefile
├── requirements.txt
└── pytest.ini
```

---

## Verified Working State

Run these to confirm everything is healthy:

```powershell
# All 7 tests pass
pytest tests/ -v

# Rebuild DuckDB warehouse from raw CSVs
python -m backend.pipeline.warehouse_pipeline

# Run one Prefect pipeline cycle (trains LightGBM on first run)
python -m backend.pipeline.flow

# Start the FastAPI backend (required for the HTML dashboard)
uvicorn backend.api:app --port 8000

# (Legacy) Launch Streamlit dashboard
streamlit run frontend/app.py
```

**Test result (last verified 2026-10-21):** 7 / 7 pass, 3.22s

**FastAPI endpoints (at http://localhost:8000):**
| Endpoint | Method | What it returns |
|---|---|---|
| `/api/forecast?city=karachi` | GET | Real LightGBM q10/q50/q90 for 168 hours |
| `/api/weather?city=karachi` | GET | Live DuckDB rows + avg/max/humidity stats |
| `/api/manifest` | GET | `manifest.csv` as JSON array |
| `/api/status` | GET | `pipeline_status.json` (MAE, rows, freshness) |
| `/api/tariffs` | GET | NEPRA slab rates from CSV |
| `/api/chat` | POST `{question}` | RAG answer + citation + confidence |

---

## Key Metrics (Real, Not Hardcoded)

| Metric | Value |
|---|---|
| Model MAE (q50) | **0.4023 °C** |
| Baseline MAE (t-168) | **1.8795 °C** |
| Improvement over baseline | **78.6%** |
| Total dataset rows | ~52,565 |
| Training rows | 41,702 (80%) |
| Test rows | 10,426 (20%) |

---

## Data Sources

| File | Publisher | On track list |
|---|---|---|
| `open-meteo-*.csv` (3 files) | Open-Meteo / CC-BY 4.0 | ✅ Yes |
| `nepra_tariff_slabs_2024.csv` | NEPRA (nepra.org.pk) / Public Domain | ❌ No ← required |

Both sources registered in `manifest.csv` with SHA-256 checksums.

---

## What Still Needs User Action (Not Code)

These are human tasks — the code is ready but a person must do them:

- [ ] **Deploy `index.html` to Vercel** — go to `https://vercel.com/new/import?repository-url=https://github.com/Arsalna-Shaikh/Bijli-Insight-Pakistan`, click Import, leave settings as-is (auto-detects static site), click Deploy. No build command needed.
- [ ] **Run backend locally during demo** — before showing the dashboard, start: `uvicorn backend.api:app --port 8000`. The Vercel frontend calls `http://localhost:8000` — browser localhost exemption allows HTTPS→HTTP for localhost.
- [ ] **Prefect evidence window** — run `python -m backend.pipeline.flow` on a live machine from Tue 4 PM to Wed 4 PM PKT to produce `data/prefect_runs.csv` with real hourly entries
- [ ] **Hugging Face Space** — deploy `frontend/app.py` as a public HF Space (required deliverable for submission)
- [ ] **Git tag** — `git tag v1.0-final && git push origin v1.0-final`
- [ ] **Summary.pdf** — 1-page project summary PDF (write and export)
- [ ] **Demo video** — 3-minute screen recording, public link

---

## Critical Technical Facts (Don't Forget)

1. **All imports use `backend.` prefix** — e.g. `from backend.ml.quantile_model import ...`. The project root must be in `PYTHONPATH` (pytest.ini sets `pythonpath = .` so tests work from root).

2. **Model trains lazily** — `lgb_quantile_50.txt` existence is the guard. If `models/` is empty, the first call to `get_forecaster()` or `task_run_inference_and_log_status()` will train and save the models.

3. **RAG indexes lazily** — `InsightAgentRAG.collection.count() == 0` guard. PDFs must exist in `knowledge_base/` for ingestion. ChromaDB store lives at `data/chroma_db/`.

4. **Non-crossing quantiles** — enforced post-prediction with `np.maximum`. Not a model property.

5. **t-168 persistence baseline** — declared baseline is `ŷ(t) = y(t-168)` (same hour last week). This was declared before training; see `Dataset_Declaration.md`.

6. **SHA-256 tamper detection** — `warehouse_pipeline.py` re-hashes all raw CSVs on every run and raises `ValueError` if any byte changed.

7. **Disqualification risks** — previously had 3 hardcoded/faked outputs. All fixed. See `docs/fix.md` for details.

8. **NEPRA tariff data** — lives in `data/raw/nepra_tariff_slabs_2024.csv`. Tab 4 bill calculator reads from this CSV via `load_tariff_slabs()`. No hardcoded rates anywhere.

---

## Architecture in One Diagram

```
data/raw/*.csv  (Open-Meteo × 3 cities + NEPRA tariff)
      │
      ▼
backend/pipeline/generate_manifest.py   → SHA-256 audit ledger
      │
      ▼
backend/pipeline/warehouse_pipeline.py
      ├── Layer 1: verify_raw_manifest()         (tamper detection)
      ├── Layer 2: build_cleaned_layer()          → DuckDB: cleaned_weather
      └── Layer 3: build_processed_gold_layer()   → DuckDB: gold_weather_features
                                                    (lag_1, lag_24, lag_168, rolling_24)
      │
      ▼
backend/ml/quantile_model.py            → LightGBM q10/q50/q90 (pinball loss)
backend/ml/model_evaluator.py           → MAE vs t-168 baseline, group slices

EVERY HOUR (Prefect cron 5 * * * *)
Open-Meteo API  → backend/pipeline/flow.py
      ├── task 1: fetch live observation
      ├── task 2: DQA (FIX → FILL → FLAG)       → quality_log.json
      ├── task 3: append to cleaned_weather
      └── task 4: real inference                 → pipeline_status.json
                                                    prefect_runs.csv

API LAYER (local, uvicorn backend.api:app --port 8000)
backend/api.py  → FastAPI with CORS(*)
      ├── GET  /api/forecast   → Open-Meteo future weather + LightGBM q10/q50/q90 (168h)
      ├── GET  /api/weather    → DuckDB gold_weather_features rows + stats
      ├── GET  /api/manifest   → manifest.csv as JSON
      ├── GET  /api/status     → pipeline_status.json (MAE, rows, freshness)
      ├── GET  /api/tariffs    → nepra_tariff_slabs_2024.csv as JSON
      └── POST /api/chat       → InsightAgentRAG retrieval + citation

DASHBOARD (index.html on Vercel, calls http://localhost:8000)
      ├── 7-day forecast chart  (real q10/q50/q90 via /api/forecast)
      ├── Warehouse data table  (real DuckDB via /api/weather)
      ├── Pipeline status KPIs  (real MAE via /api/status)
      ├── NEPRA bill calculator (real rates via /api/tariffs)
      └── Policy AI chatbot     (real RAG via /api/chat)
```

---

## Session Log

### Session 1 — 2026-10-21
**What was done:**
- Read entire project, identified 3 disqualifying hardcoded/faked outputs in `flow.py`, `app.py` Tab 3, `app.py` Tab 5
- Implemented 3 `NotImplementedError` stubs in `data_fetcher.py`
- Created `data/raw/nepra_tariff_slabs_2024.csv` as second independent data source (NEPRA, not on track list)
- Fixed `flow.py` `task_run_inference_and_log_status()` — replaced fake `model_mae=0.42` with real LightGBM inference
- Fixed `app.py` Tab 3 — replaced `np.random.normal` with real `QuantileEnergyForecaster.predict_intervals()`
- Fixed `app.py` Tab 5 — replaced `if "26" in query` keyword matching with real `InsightAgentRAG` + ChromaDB
- Fixed `app.py` Tab 4 — replaced hardcoded tariff rates with `load_tariff_slabs()` CSV reader
- Fixed `generate_manifest.py` — NEPRA files now get correct publisher/licence
- Fixed `tests/test_fetcher.py` — added missing `import pandas as pd`
- Created `AI_Use_Log.md`, `Dataset_Declaration.md`, `docs/fix.md`
- Verified real metrics: MAE 0.4023, baseline 1.8795, improvement 78.6%
- Tests: 7/7 pass

**What was not done (still pending):** See "What Still Needs User Action" above.

### Session 2 — 2026-10-21
**What was done:**
- Restructured folders: moved `pipeline/`, `agents/`, `ml/` into `backend/` package
- Renamed `rag_knowledge_base/` → `knowledge_base/`
- Created `docs/` folder; moved `current_flow.md`, `project_flow.md`, `fix.md`, `hackathonguide.md` into it
- Updated all imports across 8 files to use `backend.` prefix
- Updated `Makefile` commands to `python -m backend.pipeline.*`
- Updated `frontend/app.py` path references from `rag_knowledge_base/` → `knowledge_base/`
- Verified: 7/7 tests still pass after restructure
- Created `HANDOFF.md` (this file)
- Updated `docs/project_flow.md` and `docs/current_flow.md` to reflect new paths

### Session 3 — 2026-10-21
**What was done:**
- Replaced Streamlit dashboard with a polished single-page HTML app (`index.html`) — full responsive UI, no Python needed in browser
- Created `backend/api.py` — FastAPI with 6 endpoints (forecast, weather, manifest, status, tariffs, chat) + CORS wildcard
- `/api/forecast` calls Open-Meteo forecast API for future humidity/wind, builds lag features from DuckDB history, runs real LightGBM → returns 168-hour q10/q50/q90 arrays. Verified: Karachi hour 0 = q10 16.15 / q50 17.71 / q90 19.93 °C
- Slimmed `requirements.txt` for deployment (removed streamlit, prefect, scikit-learn, pytest)
- Created `Procfile` (`web: uvicorn backend.api:app --host 0.0.0.0 --port $PORT`)
- Committed trained LightGBM models (`models/lgb_quantile_*.txt`, 864 KB total) to git
- Committed ChromaDB vector store (`data/chroma_db/`, 1.4 MB) to git
- Committed knowledge_base PDFs to git (`neeca_policy_2022.pdf`, `neeca_residential_ecbc.pdf`, 2.6 MB)
- Updated all 7 fake sections in `index.html` to real `fetch()` calls to the FastAPI backend:
  - Sine-wave `draw()` → `loadForecast()` hitting `/api/forecast`
  - Hardcoded rows → `loadWeather()` hitting `/api/weather`
  - Hardcoded rates → real fetch from `/api/tariffs`
  - Hardcoded manifest → real fetch from `/api/manifest`
  - Keyword-matching chatbot (`if "26" in query`) → real RAG via `/api/chat`
- Set `const API = 'http://localhost:8000'` in `index.html` (localhost exemption allows HTTPS Vercel page → HTTP localhost without mixed-content block)
- Pushed all changes to GitHub (`Arsalna-Shaikh/Bijli-Insight-Pakistan`)
- **Vercel MCP got 403** (token scope mismatch on hobby personal account) — workaround: deploy manually at `vercel.com/new`, import from GitHub, click Deploy

**What was not done (still pending):**
- Vercel deploy (user action needed — see "What Still Needs User Action")
- Prefect evidence window, HF Space, git tag, Summary.pdf, demo video
