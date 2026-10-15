"""Create the `flood_exposure.kerr_2025_07_04_*` views the impact extractor reads.

Runs db/exposure_views.sql through the same connection settings as the
ingestion scripts (.env / DATABASE_URL / PG* variables), so no local `psql`
client is needed. The SQL is CREATE ... IF NOT EXISTS / CREATE OR REPLACE, so
re-running is safe.

Usage:
    python -m scripts.apply_exposure_views
"""
import sys
from pathlib import Path

from lib.db import get_engine

VIEWS_SQL = Path(__file__).resolve().parent.parent / "db" / "exposure_views.sql"


def main() -> int:
    with get_engine().begin() as conn:
        conn.exec_driver_sql(VIEWS_SQL.read_text(encoding="utf-8"))
        views = conn.exec_driver_sql(
            "SELECT table_name FROM information_schema.views "
            "WHERE table_schema = 'flood_exposure' ORDER BY table_name"
        ).scalars().all()
    print(f"Applied {VIEWS_SQL.name}: {', '.join(f'flood_exposure.{v}' for v in views)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
