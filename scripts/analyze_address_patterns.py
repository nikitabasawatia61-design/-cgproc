import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scraper.gem_pdf import download_bid_pdf, extract_consignee_blocks, pdf_to_text

data = json.loads((ROOT / "docs/data/gem-tenders.json").read_text(encoding="utf-8"))
tenders = data["tenders"]

section_re = re.compile(
    r"/Consignees/Reporting Officer and Quantity(.+?)(?:/Buyer Added Bid Specific|Checklist of the documents|$)",
    re.IGNORECASE | re.DOTALL,
)

stats = {"no_section": 0, "section_no_block": 0, "has_block": 0}
lines_out = []

for tender in tenders:
    text = pdf_to_text(download_bid_pdf(tender["gem_id"]))
    match = section_re.search(text)
    blocks = extract_consignee_blocks(text)
    has_addr = bool((tender.get("address") or "").strip())

    if not match:
        stats["no_section"] += 1
        lines_out.append(f"NO_SECTION {tender['tender_no']} {tender['gem_id']}")
        continue

    if blocks:
        stats["has_block"] += 1
    else:
        stats["section_no_block"] += 1
        snippet = match.group(1)[:400]
        lines_out.append(f"FAIL {tender['tender_no']} saved_addr={has_addr}")
        lines_out.append(snippet)
        lines_out.append("")

lines_out.insert(0, str(stats))
(ROOT / "scripts/address_patterns.txt").write_text("\n".join(lines_out), encoding="utf-8")
print(stats)
