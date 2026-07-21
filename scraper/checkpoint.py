import json
from datetime import datetime
from pathlib import Path

CHECKPOINT_PATH = Path(__file__).resolve().parent.parent / ".scraper_listing_checkpoint.json"


def save_listing_checkpoint(portal_numbers, last_page, scan_completed):
    payload = {
        "portal_numbers": sorted(str(n).strip() for n in portal_numbers),
        "last_page": last_page,
        "scan_completed": scan_completed,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    }
    CHECKPOINT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load_listing_checkpoint():
    if not CHECKPOINT_PATH.exists():
        return set(), 1, False

    try:
        payload = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set(), 1, False

    numbers = {str(n).strip() for n in payload.get("portal_numbers", []) if str(n).strip()}
    last_page = int(payload.get("last_page") or 1)
    scan_completed = bool(payload.get("scan_completed"))
    return numbers, last_page, scan_completed


def clear_listing_checkpoint():
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()
