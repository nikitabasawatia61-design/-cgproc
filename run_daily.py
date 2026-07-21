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
        from scraper.checkpoint import load_listing_checkpoint

        checkpoint_numbers, _, checkpoint_done = load_listing_checkpoint()
        saved_count = len(db.get_existing_tender_numbers())
        result = {
            "new": 0,
            "skipped": 0,
            "portal_total": len(checkpoint_numbers),
            "scan_completed": checkpoint_done,
            "missing_after_scan": max(len(checkpoint_numbers) - saved_count, 0),
            "error": str(error),
        }

    if args.export_json:
        updated = db.backfill_area_city(force_all=True)
        if updated:
            print(f"Refreshed area/city for {updated} tenders")
        path = db.export_to_json()
        if result.get("portal_total"):
            import json

            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["stats"]["portal_listing_total"] = result["portal_total"]
            payload["stats"]["missing_on_portal"] = result.get("missing_after_scan", 0)
            payload["stats"]["listing_scan_completed"] = result.get("scan_completed", False)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Exported data to {path}")
        stats = db.get_stats()
        print(f"Open tenders in dashboard: {stats['total']}")
        if stats.get("closed"):
            print(f"Closed tenders in dashboard: {stats['closed']}")
        if result.get("portal_total"):
            print(f"Portal listing total: {result['portal_total']}")
            print(f"Still missing from portal: {result.get('missing_after_scan', 0)}")

    if result.get("error"):
        print(f"Scraper finished with error: {result['error']}")
        if result.get("portal_total") or args.export_json:
            print("Partial progress was saved. Re-run the same command to resume.")
            sys.exit(0 if args.export_json else 1)
        sys.exit(1)

    print(
        f"Done. {result['new']} new tenders added. "
        f"Portal listing: {result.get('portal_total', 0)}. "
        f"Still missing: {result.get('missing_after_scan', 0)}."
    )


if __name__ == "__main__":
    main()
