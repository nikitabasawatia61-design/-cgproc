"""
Daily tender fetch script.

Manual scrape (visible browser — recommended):
    python run_daily.py --import-json --export-json

Scheduled / background:
    python run_daily.py --headless --import-json --export-json
"""

import argparse
import json
import sys
from pathlib import Path

import database as db
from scraper.runner import run_scraper

EXCEL_FILE = Path(__file__).parent / "tender_results.xlsx"


def write_export_stats(path, result):
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["stats"]["portal_listing_total"] = result.get("portal_total", 0)
    payload["stats"]["missing_on_portal"] = result.get("missing_after_scan", 0)
    payload["stats"]["listing_scan_completed"] = result.get("scan_completed", False)
    payload["stats"]["open_saved"] = result.get("open_saved", payload["stats"].get("total", 0))
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Fetch new tenders from CG e-procurement")
    parser.add_argument("--headless", action="store_true", help="Run browser headless (for scheduled tasks)")
    parser.add_argument("--import-excel", action="store_true", help="Import existing Excel data first")
    parser.add_argument("--import-json", action="store_true", help="Import existing JSON data first")
    parser.add_argument("--export-json", action="store_true", help="Export results to docs/data/tenders.json")
    parser.add_argument(
        "--full-scan",
        action="store_true",
        help="Scan every listing page (slow). Default: stop at first page with no new tenders.",
    )
    args = parser.parse_args()

    db.init_db()

    if args.import_json:
        try:
            count = db.import_from_json()
            print(f"Imported {count} tenders from JSON")
        except ValueError as error:
            print(f"ERROR: {error}")
            sys.exit(1)

    if args.import_excel and EXCEL_FILE.exists():
        count = db.import_from_excel(EXCEL_FILE)
        print(f"Imported {count} tenders from {EXCEL_FILE}")

    print("Starting tender fetch...")
    try:
        result = run_scraper(headless=args.headless, full_scan=args.full_scan)
    except Exception as error:
        print(f"Scraper crashed: {error}")
        result = {
            "new": 0,
            "skipped": 0,
            "portal_total": 0,
            "scan_completed": False,
            "missing_after_scan": 0,
            "open_saved": db.get_stats()["total"],
            "error": str(error),
        }

    if args.export_json:
        updated = db.backfill_area_city(force_all=True)
        if updated:
            print(f"Refreshed area/city for {updated} tenders")
        path = db.export_to_json()
        if result.get("portal_total"):
            write_export_stats(path, result)
        print(f"Exported data to {path}")

    if result.get("error"):
        print(f"Scraper finished with error: {result['error']}")
        sys.exit(1 if not args.export_json else 0)

    print(
        f"Done. Open saved: {result.get('open_saved', 0)}. "
        f"On portal: {result.get('portal_total', 0)}. "
        f"Still to fetch: {result.get('missing_after_scan', 0)}."
    )


if __name__ == "__main__":
    main()
