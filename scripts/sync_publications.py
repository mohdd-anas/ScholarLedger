"""CLI entry point for scheduled publication sync.

Run via cron inside Docker Compose:
    docker compose exec app python scripts/sync_publications.py --source orcid
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import get_session_factory  # noqa: E402
from app.services.sync_service import run_sync  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description="Sync publications from external sources")
    parser.add_argument(
        "--source",
        choices=["orcid", "openalex", "crossref", "all"],
        default="all",
        help="Which source to sync from",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    args = parser.parse_args()

    session_factory = get_session_factory()
    db = session_factory()
    try:
        runs = asyncio.run(run_sync(db, source=args.source, dry_run=args.dry_run))
        for r in runs:
            print(
                f"[{r.source}] status={r.status.value} "
                f"fetched={r.records_fetched} merged={r.records_merged} queued={r.records_queued}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
