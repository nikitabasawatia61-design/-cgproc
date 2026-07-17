"""
Fetch GeM BidPlus tenders for Chhattisgarh / Korba and export JSON for the dashboard.

Run manually:
    python run_gem.py --export-json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from scraper.dates import is_tender_closed
from scraper.gem import DEFAULT_CITY, DEFAULT_STATE, fetch_gem_tenders

GEM_JSON = Path(__file__).parent / "docs" / "data" / "gem-tenders.json"


def load_existing(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def merge_tenders(existing: dict, fresh: list[dict]) -> list[dict]:
    previous = {
        item["tender_no"]: item
        for item in existing.get("tenders", [])
        if item.get("tender_no")
    }
    merged = []
    for tender in fresh:
        old = previous.get(tender["tender_no"])
        if old:
            tender["first_seen_at"] = old.get("first_seen_at") or tender["first_seen_at"]
        merged.append(tender)
    return merged


def build_stats(tenders: list[dict]) -> dict:
    active = [t for t in tenders if not is_tender_closed(t.get("last_date"))]
    today = datetime.now().strftime("%Y-%m-%d")
    new_today = sum(
        1 for tender in active
        if (tender.get("first_seen_at") or "").startswith(today)
    )
    last_scraped = datetime.now().isoformat(timespec="seconds")
    return {
        "total": len(active),
        "new_today": new_today,
        "last_scraped": last_scraped,
    }


def export_gem_json(
    tenders: list[dict],
    *,
    state_name: str,
    city_name: str,
    path: Path = GEM_JSON,
) -> Path:
    active = [t for t in tenders if not is_tender_closed(t.get("last_date"))]
    active.sort(
        key=lambda item: (
            item.get("first_seen_at") or "",
            item.get("tender_no") or "",
        ),
        reverse=True,
    )

    payload = {
        "exported_at": datetime.now().isoformat(timespec="seconds"),
        "source": "gem",
        "filters": {
            "state": state_name,
            "city": city_name,
        },
        "stats": build_stats(active),
        "tenders": active,
    }

    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
    return path


def main():
    parser = argparse.ArgumentParser(description="Fetch GeM BidPlus tenders")
    parser.add_argument("--export-json", action="store_true", help="Write docs/data/gem-tenders.json")
    parser.add_argument("--state", default=DEFAULT_STATE, help="State filter for GeM search")
    parser.add_argument("--city", default=DEFAULT_CITY, help="City filter for GeM search")
    args = parser.parse_args()

    print(f"Fetching GeM tenders for {args.state} / {args.city}...")
    try:
        fresh = fetch_gem_tenders(state_name=args.state, city_name=args.city)
    except Exception as error:
        print(f"GeM fetch failed: {error}")
        sys.exit(1)

    print(f"Fetched {len(fresh)} bids from GeM")

    if args.export_json:
        existing = load_existing(GEM_JSON)
        merged = merge_tenders(existing, fresh)
        path = export_gem_json(
            merged,
            state_name=args.state,
            city_name=args.city,
        )
        stats = build_stats(merged)
        print(f"Exported {stats['total']} active GeM tenders to {path}")
        print(f"New today: {stats['new_today']}")


if __name__ == "__main__":
    main()
