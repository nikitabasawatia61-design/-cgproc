import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper.gem_pdf import download_bid_pdf, extract_consignee_blocks, pdf_to_text

data = json.loads((ROOT / "docs/data/gem-tenders.json").read_text(encoding="utf-8"))
empty = [t for t in data["tenders"] if not (t.get("address") or "").strip()]
filled = [t for t in data["tenders"] if (t.get("address") or "").strip()]

lines = []
for label, tender in [("EMPTY", empty[0]), ("EMPTY2", empty[1]), ("FILLED", filled[0])]:
    text = pdf_to_text(download_bid_pdf(tender["gem_id"]))
    idx = text.lower().find("consignee")
    lines.append(f"=== {label} {tender['tender_no']} {tender['gem_id']} ===")
    lines.append(text[idx : idx + 900] if idx >= 0 else "NO CONSIGNEE")
    lines.append(f"blocks: {extract_consignee_blocks(text)}")
    lines.append("")

(ROOT / "scripts/address_debug.txt").write_text("\n".join(lines), encoding="utf-8")
print("written to scripts/address_debug.txt")
