"""CLI subcommands for Contract 2 impact extraction."""
from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path
import sys

from flood.engine.run import Run
from flood.impact.extractor import (
    PROJECTION_OFFSETS_MIN,
    ImpactExtractionError,
    ImpactExtractor,
    impact_path,
    write_impact_json,
)
from flood.impact.postgis import ExposureConfigError, ExposureDataError, PostGISExposureStore, resolve_dsn
from flood.contracts.validate import ContractError
from flood.interfaces import TimeGridError
from flood.scenario import load_scenario


def _materialize(run: Run, p, t) -> Path:
    """Write the (p, t) depth COG if it is not already on disk, and return its path."""
    run.state(p if p is not None else "hindsight", t, write=True)
    return run.product_path("raster", p if p is not None else "hindsight", t)


def run_impacts_extract(args: argparse.Namespace) -> int:
    """Resolve the engine query, materialize its products, and write Contract 2."""
    scenario_path = Path(args.scenario)
    if not scenario_path.exists():
        print(f"Error: Scenario not found: {scenario_path}", file=sys.stderr)
        return 2
    run_dir = Path(args.run_dir)
    if not (run_dir / "run.json").is_file():
        print(f"Error: Run manifest not found: {run_dir / 'run.json'}", file=sys.stderr)
        return 2

    try:
        scenario = load_scenario(scenario_path)
        run = Run.open(run_dir, args.data_dir or run_dir.parent.parent / "data")
        resolved = run.resolve(args.p, args.t)

        current = _materialize(run, resolved.p, resolved.t)
        reaches = run.product_path(
            "reaches", resolved.p if resolved.mode != "hindsight" else "hindsight", resolved.t
        )

        # Same-`p` projections, but only for targets Contract 1 still permits.
        projections: dict = {}
        for offset in PROJECTION_OFFSETS_MIN:
            t_future = resolved.t + timedelta(minutes=offset)
            try:
                run.resolve(args.p, t_future)
            except TimeGridError:
                continue  # Outside the record or horizon: omit, never substitute.
            projections[t_future] = _materialize(run, resolved.p, t_future)

        store = PostGISExposureStore(resolve_dsn(args.postgis_dsn))
        extractor = ImpactExtractor(scenario, store)
        payload = extractor.extract(
            run_id=run.run_id,
            p=resolved.p,
            t=resolved.t,
            current_cog=current,
            projection_cogs=projections,
            reaches_parquet=reaches if reaches.exists() else None,
        )
        out_path = write_impact_json(impact_path(run_dir, resolved.p, resolved.t), payload)
    except (ExposureConfigError, ExposureDataError) as err:
        print(f"Error: exposure configuration: {err}", file=sys.stderr)
        return 2
    except ImpactExtractionError as err:
        print(f"Error: missing or inconsistent engine product: {err}", file=sys.stderr)
        return 2
    except TimeGridError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 2
    except ContractError as err:
        print(f"Error: written document violates Contract 2: {err}", file=sys.stderr)
        return 2

    print(out_path)
    return 0


def prewarmed_queries(run_dir: Path, data_dir: Path | None = None) -> list[tuple[str, str]]:
    """Every (p, t) the API can serve with precomputed=1, hindsight first, as CLI strings."""
    run = Run.open(run_dir, data_dir or run_dir.parent.parent / "data")
    forward, hindsight = run.precomputed_index()
    queries = [("hindsight", t.strftime("%Y-%m-%dT%H:%M:%SZ")) for t in sorted(hindsight)]
    for p in sorted(forward):
        for t in sorted(forward[p]):
            queries.append((p.strftime("%Y-%m-%dT%H:%M:%SZ"), t.strftime("%Y-%m-%dT%H:%M:%SZ")))
    return queries


def pending_queries(run_dir: Path, data_dir: Path | None = None, force: bool = False) -> list[tuple[str, str]]:
    """The prewarmed queries still lacking an impact.json (all of them with `force`)."""
    from flood.timegrid import parse_iso

    todo = []
    for p, t in prewarmed_queries(run_dir, data_dir):
        p_dt = None if p == "hindsight" else parse_iso(p)
        if force or not impact_path(run_dir, p_dt, parse_iso(t)).is_file():
            todo.append((p, t))
    return todo


def _extract_one(args: argparse.Namespace, p: str, t: str) -> tuple[str, str, int]:
    one = argparse.Namespace(**{**vars(args), "p": p, "t": t})
    return p, t, run_impacts_extract(one)


def run_impacts_extract_prewarmed(args: argparse.Namespace) -> int:
    """Extract Contract 2 for every prewarmed (p, t), skipping ones already written."""
    from concurrent.futures import ProcessPoolExecutor, as_completed

    run_dir = Path(args.run_dir)
    if not (run_dir / "run.json").is_file():
        print(f"Error: Run manifest not found: {run_dir / 'run.json'}", file=sys.stderr)
        return 2
    try:
        resolve_dsn(args.postgis_dsn)  # fail fast, before any work, when no DSN is configured
    except ExposureConfigError as err:
        print(f"Error: exposure configuration: {err}", file=sys.stderr)
        return 2

    todo = pending_queries(run_dir, Path(args.data_dir) if args.data_dir else None, args.force)
    print(f"{len(todo)} prewarmed queries to extract ({args.jobs} at a time)", file=sys.stderr)

    failed = 0
    with ProcessPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(_extract_one, args, p, t) for p, t in todo]
        for done, fut in enumerate(as_completed(futures), 1):
            p, t, code = fut.result()
            failed += code != 0
            status = "ok" if code == 0 else f"FAILED (exit {code})"
            print(f"[{done}/{len(todo)}] p={p} t={t} {status}", file=sys.stderr)
    return 1 if failed else 0


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register the 'impacts' subcommand group."""
    impacts = subparsers.add_parser("impacts", help="Contract 2 impact products")
    impacts_sub = impacts.add_subparsers(dest="impacts_command", required=True)
    extract = impacts_sub.add_parser("extract", help="Extract Contract 2 facts for a (p, t) query")
    extract.add_argument("--scenario", required=True, help="Path to the scenario JSON")
    extract.add_argument("--run-dir", required=True, help="Path to the run directory")
    extract.add_argument("--p", required=True, help="Knowledge cutoff (ISO UTC) or 'hindsight'")
    extract.add_argument("--t", required=True, help="Target time (ISO UTC)")
    extract.add_argument("--postgis-dsn", default=None, help="PostGIS DSN; else FLOOD_POSTGIS_DSN")
    extract.add_argument("--data-dir", default=None, help="Data directory for the run")
    extract.set_defaults(func=run_impacts_extract)

    prewarmed = impacts_sub.add_parser(
        "extract-prewarmed",
        help="Extract Contract 2 facts for every prewarmed (p, t) in a run (feeds the live heatmap)",
    )
    prewarmed.add_argument("--scenario", required=True, help="Path to the scenario JSON")
    prewarmed.add_argument("--run-dir", required=True, help="Path to the run directory")
    prewarmed.add_argument("--postgis-dsn", default=None, help="PostGIS DSN; else FLOOD_POSTGIS_DSN")
    prewarmed.add_argument("--data-dir", default=None, help="Data directory for the run")
    prewarmed.add_argument("--jobs", type=int, default=4, help="Parallel extractions (default 4)")
    prewarmed.add_argument("--force", action="store_true", help="Re-extract queries already written")
    prewarmed.set_defaults(func=run_impacts_extract_prewarmed)
