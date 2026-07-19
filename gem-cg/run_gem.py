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
from scraper.gem_pdf import enrich_tender

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
            for key in (
                "documents_required_from_seller",
                "address",
                "additional_requirement",
                "consignee",
                "consignees",
                "pdf_url",
            ):
                if old.get(key) and not tender.get(key):
                    tender[key] = old[key]
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


def enrich_tenders(tenders: list[dict]) -> list[dict]:
    import requests

    session = requests.Session()
    enriched = []
    total = len(tenders)
    for index, tender in enumerate(tenders, start=1):
        print(f"PDF {index}/{total}: {tender.get('tender_no', 'unknown')}")
        enriched.append(enrich_tender(dict(tender), session=session))
    return enriched


def main():
    parser = argparse.ArgumentParser(description="Fetch GeM BidPlus tenders")
    parser.add_argument("--export-json", action="store_true", help="Write docs/data/gem-tenders.json")
    parser.add_argument("--enrich-pdf", action="store_true", help="Download bid PDFs and extract seller docs/address")
    parser.add_argument("--enrich-only", action="store_true", help="Only enrich existing gem-tenders.json (no list fetch)")
    parser.add_argument("--state", default=DEFAULT_STATE, help="State filter for GeM search")
    parser.add_argument("--city", default=DEFAULT_CITY, help="City filter for GeM search")
    args = parser.parse_args()

    if args.enrich_only:
        existing = load_existing(GEM_JSON)
        tenders = existing.get("tenders", [])
        if not tenders:
            print("No tenders in gem-tenders.json")
            sys.exit(1)
        print(f"Enriching {len(tenders)} tenders from PDFs...")
        enriched = enrich_tenders(tenders)
        filters = existing.get("filters", {"state": args.state, "city": args.city})
        path = export_gem_json(
            enriched,
            state_name=filters.get("state", args.state),
            city_name=filters.get("city", args.city),
        )
        print(f"Exported enriched data to {path}")
        return

    print(f"Fetching GeM tenders for {args.state} / {args.city}...")
    try:
        fresh = fetch_gem_tenders(state_name=args.state, city_name=args.city)
    except Exception as error:
        print(f"GeM fetch failed: {error}")
        sys.exit(1)

    print(f"Fetched {len(fresh)} bids from GeM")

    if args.enrich_pdf:
        print("Reading bid PDFs for document/address details...")
        fresh = enrich_tenders(fresh)

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
