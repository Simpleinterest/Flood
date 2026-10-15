# Ingestion

This folder loads the Kerr County map layers (roads, rivers, buildings and road–stream crossings) from public TxDOT, USGS and FEMA services into a local PostGIS database. The physics engine reads those layers to work out which features are flooded, and the 3D verifier's live vulnerability heatmap is built from them. The folder also holds the historical critic: a RAG service that reviews a proposed plan against after-action reports and cites them. You only need the database once, to generate the heatmap's impact files; after that, everything runs from files.

## Run it

Needs Python 3.12+ and Docker. Run from `ingestion/`:

```bash
docker compose up -d postgis
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

python -m scripts.fetch_kerr_county_boundary
python -m scripts.ingest_txdot_roads
python -m scripts.ingest_nhd_flowlines
python -m scripts.ingest_fema_buildings
python -m scripts.ingest_usgs_crossings
python -m scripts.verify_exposure_layers
python -m scripts.apply_exposure_views
```

If `ingest_nhd_flowlines` fails with a `504 Gateway Timeout`, the USGS service is down. Load the same data from USGS's static download instead:

```bash
curl -O https://prd-tnm.s3.amazonaws.com/StagedProducts/Hydrography/NHDPlusHR/Beta/GDB/NHDPLUS_H_1210_HU4_GDB.zip
unzip NHDPLUS_H_1210_HU4_GDB.zip
python -m scripts.ingest_nhd_flowlines --from-file NHDPLUS_H_1210_HU4_GDB.gdb
```

Then build the heatmap's impact files from the repository root (30–60 min, resumable):

```bash
export FLOOD_POSTGIS_DSN=postgresql://flood:flood@localhost:5432/flood
.venv/bin/flood impacts extract-prewarmed --scenario scenarios/kerr-2025-07-04.json \
  --run-dir runs/kerr-2025-07-04-replay-fe0f78 --jobs 6
```

After that, PostGIS can be stopped with `docker compose down`.

**Critic (RAG plan review):** build an AAR index from your own report PDFs (`python -m aar build`; see the reference below), then run with your own OpenAI key. The critic reads these from the environment, not from `.env`:

```bash
export OPENAI_API_KEY=sk-...
AAR_INDEX_DIR=../data/aar/library uvicorn critic.app:app --port 8001
```

Tests: `pytest`. Full reference (sources, camps, critic, RAGAS evaluation, IPAWS tool): [`docs/ingestion.md`](../docs/ingestion.md).
