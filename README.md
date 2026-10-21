---
title: Bijli-Insight Pakistan
emoji: ⚡
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: 1.39.0
app_file: frontend/app.py
pinned: false
license: mit
---

# Bijli-Insight Pakistan · بجلی بصیرت پاکستان

Hourly heat forecasts with honest uncertainty for Karachi, Lahore and Islamabad. Temperature is the main driver of cooling demand, so the forecasts are turned into grid and household guidance: when to avoid heavy load, what a NEPRA bill will cost, and what NEECA/NEPRA documents actually say.

**HackInsight 2026 · Energy Demand track**

- **Live dashboard:** https://bijli-insight-pakistan.vercel.app
- **Live API:** https://bijli-insight-api.onrender.com/api/status (free tier; the first request after idle takes about 50 s)

## Results

Read from `data/pipeline_status.json`, written by the pipeline's last run. The dashboard shows the same file via `/api/status`.

| Metric | Value |
|---|---|
| Model MAE, median (q50) | **0.4023 °C** |
| Declared baseline MAE (same hour last week, t − 168) | **1.8795 °C** |
| Error reduction vs baseline | **78.6%** |
| Warehouse | 52,632 hourly rows, 3 cities, 2024–2025 |
| Train / test | Chronological 80/20 (41,702 / 10,426), no shuffling |
| Tests | 21 passing (`pytest tests/`) |

## How it works

| Stage | What it does | Code |
|---|---|---|
| Ingest + verify | Open-Meteo/PMD hourly CSVs and NEPRA tariffs, each fingerprinted with SHA-256; the build refuses to run if a file changes | `backend/pipeline/data_fetcher.py`, `generate_manifest.py` |
| Warehouse | DuckDB in three layers: raw → `cleaned_weather` → `gold_weather_features` (lags t−1/24/168, 24 h rolling mean, no leakage) | `backend/pipeline/warehouse_pipeline.py` |
| Data quality | **FIX** types, **FILL** short gaps (`is_imputed`), **FLAG** implausible values (`is_anomalous`), logged to `quality_log.json` | `backend/agents/data_quality_agent.py` |
| Forecast | Three LightGBM models with pinball loss → q10 / q50 / q90, non-crossing enforced | `backend/ml/quantile_model.py` |
| Evaluate | MAE vs the t−168 baseline, declared before training | `backend/ml/model_evaluator.py` |
| Orchestrate | Prefect flow every hour (`5 * * * *`): fetch → audit → append → re-infer | `backend/pipeline/flow.py` |
| Policy advisor | RAG over ChromaDB; a Groq LLM answers only from the retrieved passages, citations come from document metadata, and it says "I don't know" otherwise | `backend/agents/insight_rag_agent.py`, `backend/pipeline/build_knowledge_base.py` |
| Serve | FastAPI on Render; static dashboard on Vercel | `backend/api.py`, `index.html` |

The advisor's knowledge base covers three sources:
- NEECA National Energy Policy 2022 (PDF).
- NEECA's building-sector guidance, a scanned PDF indexed from its committed OCR transcription.
- The NEPRA 2024 residential tariff slabs.

Missing sources are indexed automatically when the API starts.

### API

| Endpoint | Returns |
|---|---|
| `GET /api/forecast?city=karachi` | 168 hourly q10 / q50 / q90 values |
| `GET /api/weather?city=&table=&limit=` | Warehouse rows and summary stats |
| `GET /api/status` | Last pipeline run: MAE, baseline, improvement, freshness, record count |
| `GET /api/manifest` | Source files with licence, row count, SHA-256 |
| `GET /api/tariffs` | NEPRA slab rates |
| `POST /api/chat` `{question}` | Grounded Markdown answer, source, fallback flag |
| `GET /health` | Liveness |

## Run locally

```bash
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt pytest prefect
echo GROQ_API_KEY=your_key > .env                    # optional; enables LLM answers in the advisor

pytest tests/ -v
python -m backend.pipeline.warehouse_pipeline        # rebuild the warehouse
python -m backend.pipeline.flow                      # one pipeline cycle (trains models if missing)
python -m backend.pipeline.build_knowledge_base      # rebuild the advisor's index
uvicorn backend.api:app --port 8000                  # API; then open index.html
```

`index.html` calls `localhost:8000` when served locally, and the Render API everywhere else. A Streamlit version runs with `streamlit run frontend/app.py`.

## Repository

```
index.html          Dashboard (Vercel)
backend/            api.py · pipeline/ · agents/ · ml/
frontend/app.py     Streamlit dashboard (Hugging Face Space)
data/               raw CSVs + manifest, warehouse.duckdb, chroma_db, pipeline status and logs
models/             Trained LightGBM q10 / q50 / q90
knowledge_base/     NEECA PDFs and the OCR transcription
tests/              pytest suite
docs/               Architecture walkthroughs, product brief, design system
render.yaml         API deploy (Render)    ·    vercel.json  Dashboard deploy (Vercel)
```

## Limitations

- Temperature is a **proxy** for cooling demand; the system does not forecast MW load.
- Bill estimates use NEPRA 2024 slabs, with taxes approximated at 17%.
- The advisor only knows its three sources; anything outside them gets "I don't know".

## Submission documents

[`Dataset_Declaration.md`](Dataset_Declaration.md) (sources, licences, declared baseline) · [`AI_Use_Log.md`](AI_Use_Log.md) · [`docs/`](docs/)
