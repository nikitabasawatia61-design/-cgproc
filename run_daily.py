"""
Daily tender fetch script.

Run manually:
    python run_daily.py

Run headless (for scheduled tasks):
    python run_daily.py --headless
"""

import argparse
import sys
from pathlib import Path

import database as db
from scraper.runner import run_scraper

EXCEL_FILE = Path(__file__).parent / "tender_results.xlsx"


def main():
    parser = argparse.ArgumentParser(description="Fetch new tenders from CG e-procurement")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--import-excel", action="store_true", help="Import existing Excel data first")
    parser.add_argument("--import-json", action="store_true", help="Import existing JSON data first")
    parser.add_argument("--export-json", action="store_true", help="Export results to docs/data/tenders.json")
    args = parser.parse_args()

    db.init_db()

    if args.import_json:
        count = db.import_from_json()
        print(f"Imported {count} tenders from JSON")

    if args.import_excel and EXCEL_FILE.exists():
        count = db.import_from_excel(EXCEL_FILE)
        print(f"Imported {count} tenders from {EXCEL_FILE}")

    print("Starting daily tender fetch...")
    try:
        result = run_scraper(headless=args.headless)
    except Exception as error:
        print(f"Scraper crashed: {error}")
        result = {
            "new": 0,
            "skipped": 0,
            "portal_total": 0,
            "removed_stale": 0,
            "error": str(error),
        }

    if args.export_json:
        updated = db.backfill_area_city(force_all=True)
        if updated:
            print(f"Refreshed area/city for {updated} tenders")
        removed = db.remove_closed_tenders()
        if removed:
            print(f"Removed {removed} closed tenders")
        path = db.export_to_json()
        print(f"Exported data to {path}")
        stats = db.get_stats()
        print(f"Open tenders in dashboard: {stats['total']}")
        if stats.get("closed"):
            print(f"Closed tenders in dashboard: {stats['closed']}")

    if result.get("error"):
        print(f"Scraper finished with error: {result['error']}")
        sys.exit(1)

    print(
        f"Done. {result['new']} new tenders added. "
        f"Portal listing: {result.get('portal_total', 0)}."
    )


if __name__ == "__main__":
    main()
