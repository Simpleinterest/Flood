
# Running the physics engine from a fresh clone

The repository tracks everything the engine needs except the HAND cube, which is 1.2 GB of dense arrays and is rebuilt locally in a few minutes from the tracked HAND files.

Tracked data:

| Path | What | Size |
|---|---|---|
| `data/hand/12100201/` | FIM 4.9.9.0 HAND branches, hydrotable, streams and lakes for HUC8 12100201 | 174 MB |
| `data/usgs/kerr-2025-07-04/` | USGS discharge and gauge height, 5 and 15 minute | under 1 MB |
| `data/nwm/kerr-2025-07-04/` | NWM analysis and short-range forecasts subset to the HUC | under 1 MB |
| `runs/kerr-2025-07-04-replay-fe0f78/` | The calibrated reference run: manifest, calibration, and the prewarmed demo window | 225 MB |

Steps (Python 3.12 or 3.13; macOS's built-in `python3` is 3.9 and too old). Commands are for macOS/Linux; on Windows, use `python` and `.venv\Scripts\` instead of `python3.12` and `.venv/bin/`.

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
```

```bash
.venv/bin/flood prep hand scenarios/kerr-2025-07-04.json
```

That reads the tracked HAND files (no download unless `--force`) and writes `data/cube/kerr-2025-07-04/`, about three minutes.

```bash
.venv/bin/flood serve --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/verifier/` (2D) or `http://127.0.0.1:8000/verifier/terrain.html` (3D). The run list puts the calibrated run first. Requests inside the prewarmed window (cutoffs 06:00 to 10:00Z, horizons 0 to 240 minutes, hindsight 06:00 to 12:00Z every 30 minutes) are served from disk in one to three seconds; anything else computes on demand, about 17 seconds cold. Pages send `precomputed=1` by default so a playing clock never triggers a computation; untick "Prewarmed only" to compute arbitrary times.

The 3D page's live vulnerability heatmap stays empty until impact files exist for the run; generate them with `flood impacts extract-prewarmed` (see the root `README.md`, step 4).

Tests: `.venv/bin/pytest`.

Do not commit `data/cube/` or new run directories unless they are meant to be shared; `.gitignore` lists exactly what is tracked.
