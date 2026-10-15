"""`flood impacts extract-prewarmed`: query selection and configuration errors (offline)."""
from __future__ import annotations

import argparse
import json

from flood import cli_impacts


def _impact(run_dir, rel):
    path = run_dir / "impacts" / rel / "impact.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({}), encoding="utf-8")


def test_pending_skips_queries_already_extracted(tmp_path, monkeypatch):
    queries = [
        ("hindsight", "2025-07-04T06:00:00Z"),
        ("hindsight", "2025-07-04T06:30:00Z"),
        ("2025-07-04T08:00:00Z", "2025-07-04T09:00:00Z"),
        ("2025-07-04T08:00:00Z", "2025-07-04T10:00:00Z"),
    ]
    monkeypatch.setattr(cli_impacts, "prewarmed_queries", lambda run_dir, data_dir=None: queries)
    _impact(tmp_path, "hindsight/t=20250704T0600Z")
    _impact(tmp_path, "p=20250704T0800Z/t=20250704T0900Z")

    assert cli_impacts.pending_queries(tmp_path) == [queries[1], queries[3]]
    assert cli_impacts.pending_queries(tmp_path, force=True) == queries


def test_missing_dsn_is_a_configuration_error_before_any_work(tmp_path, monkeypatch, capsys):
    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    monkeypatch.delenv("FLOOD_POSTGIS_DSN", raising=False)
    monkeypatch.setattr(cli_impacts, "pending_queries", lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    args = argparse.Namespace(
        scenario="unused.json", run_dir=str(tmp_path), postgis_dsn=None, data_dir=None, jobs=1, force=False
    )

    assert cli_impacts.run_impacts_extract_prewarmed(args) == 2
    assert "No PostGIS DSN" in capsys.readouterr().err
