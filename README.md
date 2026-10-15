# Flood

Flood is a decision-support and training system built on the 4 July 2025 Guadalupe River flash flood in Kerr County, Texas. A HAND-based physics engine replays the flood minute by minute and works out which roads, crossings and buildings are underwater. A demographic risk model and a hazard-fused heatmap show where vulnerable people are most likely to need help. A Command interface lets a commander review the situation, and a RAG critic stress-tests their plans against historical after-action reports.

## Run it

Needs Python 3.12+ (macOS's built-in `python3` is too old), Node 22.13+ with pnpm, and Docker for step 3. Commands are for macOS/Linux; on Windows use `.venv\Scripts\` instead of `.venv/bin/`.

**1. Physics engine** → http://127.0.0.1:8000/verifier/

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/flood prep hand scenarios/kerr-2025-07-04.json   # one-time, ~3 min
FLOOD_CLOCK_START=2025-07-04T06:00:00Z FLOOD_CLOCK_END=2025-07-04T10:00:00Z \
  .venv/bin/flood serve --port 8000   # clock limited to the prewarmed window
```

**2. Command interface** → http://localhost:3000

```bash
cd frontend && pnpm install && pnpm dev
```

**3. Map data and live heatmap (optional, one-time)**: see [`ingestion/README.md`](ingestion/README.md).

**4. RAG plan review (optional)**: needs your own AAR index and OpenAI key; see [`ingestion/README.md`](ingestion/README.md).

Tests: `.venv/bin/pytest`, `cd ingestion && .venv/bin/pytest`, `cd frontend && pnpm test`. More detail lives in `docs/`.
