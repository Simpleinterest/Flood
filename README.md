# Flood

A flood decision-support and training system built on the 4 July 2025 Guadalupe River
flash flood in Kerr County, Texas. It has four parts, each runnable on its own:

| Part | Where | What it does | Needs |
|---|---|---|---|
| Physics engine | `src/flood/` | HAND-based inundation replay, verifier pages, impact extraction | Python |
| Command interface | `frontend/` | The Command/Field UI | Node + pnpm |
| Map-data ingestion | `ingestion/` | Loads roads, rivers, buildings and crossings into PostGIS | Python + Docker |
| Historical critic (RAG) | `ingestion/critic/` | Reviews a proposed plan against past after-action reports | Python + your own AAR corpus + OpenAI key |

Design docs: `docs/PRD.md`, `docs/architecture.md`, `docs/contracts/`.

## Prerequisites

- **Python 3.12 or 3.13.** macOS's built-in `python3` is 3.9 and is too old; install a
  newer one (e.g. `brew install python@3.12`) and use it to create the virtualenvs below.
- **Node 22.13+ and pnpm** for the frontend.
- **Docker** only for map-data ingestion and impact extraction (steps 3–4).

Commands below are for macOS/Linux. On Windows, replace `.venv/bin/` with `.venv\Scripts\`.

## 1. Physics engine

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/flood prep hand scenarios/kerr-2025-07-04.json   # one-time, ~3 min, builds data/cube/
.venv/bin/flood serve --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/verifier/` (2D) or `http://127.0.0.1:8000/verifier/terrain.html` (3D).
Details: [`docs/running-the-engine.md`](docs/running-the-engine.md). Tests: `.venv/bin/pytest`.

## 2. Command interface

```bash
cd frontend
pnpm install
pnpm dev        # http://localhost:3000
```

Details: [`frontend/README.md`](frontend/README.md).

## 3. Map-data ingestion (PostGIS)

```bash
docker compose up -d postgis          # creates the tables on first start
cd ingestion
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env                  # defaults match docker-compose.yml
.venv/bin/python -m scripts.fetch_kerr_county_boundary
.venv/bin/python -m scripts.ingest_txdot_roads
.venv/bin/python -m scripts.ingest_nhd_flowlines   # see ingestion/README.md if USGS returns 504
.venv/bin/python -m scripts.ingest_fema_buildings
.venv/bin/python -m scripts.ingest_usgs_crossings
.venv/bin/python -m scripts.verify_exposure_layers
.venv/bin/python -m scripts.apply_exposure_views
```

Details, sources and the camps loader: [`ingestion/README.md`](ingestion/README.md).

## 4. Impact extraction (live vulnerability heatmap)

The 3D verifier's hazard-fused heatmap reads precomputed impact files. Generate them
once from the PostGIS layers loaded in step 3 (from the repo root):

```bash
export FLOOD_POSTGIS_DSN=postgresql://flood:flood@localhost:5432/flood
.venv/bin/flood impacts extract-prewarmed \
  --scenario scenarios/kerr-2025-07-04.json \
  --run-dir runs/kerr-2025-07-04-replay-fe0f78 --jobs 6
```

Each query takes about 30 s of CPU, so the ~260 prewarmed queries take roughly
30–60 minutes depending on `--jobs`. It skips queries already extracted, so it is
safe to stop and re-run. Extraction also materializes the +30/+60/+120/+240-minute
projection rasters, which the API then serves as precomputed too; re-running picks
those up as well. Afterwards the heatmap only reads files, so PostGIS can be stopped
(`docker compose down`).

## 5. Historical critic (RAG plan review)

The Command view's **Plan review** tab calls this service on `http://localhost:8001`.
It needs a built AAR index and an OpenAI key, neither of which is in the repository:
the source PDFs and index under `data/aar/` are gitignored, and each user supplies
their own key in `ingestion/.env`. Building the index and running the service:
[`ingestion/README.md`](ingestion/README.md#historical-flood-report-library-manual-source-handoff).
Without it, everything else still works and the tab reports "RAG review unavailable".

## What is not in the repository

| Item | How to get it |
|---|---|
| `data/cube/` (1.2 GB HAND cube) | `flood prep hand` (step 1) |
| PostGIS contents | Step 3 |
| `runs/*/impacts/` | Step 4 |
| `data/aar/` (AAR PDFs, manifest, index) | Curate your own; see step 5 |
| `ingestion/.env` (DB settings, OpenAI key) | `cp ingestion/.env.example ingestion/.env` |
| Camp footprints | Manual acquisition; see `ingestion/README.md` |
