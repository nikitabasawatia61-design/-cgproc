"""Extract key fields from GeM bid PDF documents."""

from __future__ import annotations

import io
import re
from typing import Any

import requests

PDF_URL = "https://bidplus.gem.gov.in/showbidDocument/{gem_id}"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://bidplus.gem.gov.in/",
}


def download_bid_pdf(gem_id: str, session: requests.Session | None = None) -> bytes:
    session = session or requests.Session()
    session.headers.update(HEADERS)
    url = PDF_URL.format(gem_id=gem_id)
    response = session.get(url, timeout=90)
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise RuntimeError("GeM did not return a PDF for this bid")
    return response.content


def pdf_to_text(pdf_bytes: bytes) -> str:
    try:
        import pypdf
    except ImportError as error:
        raise RuntimeError("Install pypdf: pip install pypdf") from error

    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def _clean(value: str) -> str:
    text = re.sub(r"\s+", " ", value or "").strip()
    return text.strip(" ,;.")


def extract_documents_required(text: str) -> str:
    patterns = [
        r"/Document required\s*from seller\s*(.+?)(?:\*In case any bidder|$)",
        r"Documents required from seller['\u2019]?\s*(.+?)(?:Checklist of the documents|$)",
        r"/Document required\s*from seller\s*\n(.+?)(?:\n\*In case|\n7या|\nBuyer Added|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = _clean(match.group(1))
            if cleaned and len(cleaned) > 5:
                return cleaned[:2000]
    return ""


def extract_consignee_blocks(text: str) -> list[dict[str, str]]:
    blocks = []
    section_match = re.search(
        r"/Consignees/Reporting Officer and Quantity(.+?)(?:/Buyer Added Bid Specific|Checklist of the documents|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section_match:
        return blocks

    section = section_match.group(1)
    row_match = re.search(
        r"\n1\s*\n([^\n]+)\n([^\n]+)\n\(([^\)]+)\)\s*\n"
        r"(?:Project\s*/\s*\n)?(?:Lumpsum\s*\n)?(?:Based\s*\n)?"
        r"(N/A|[^\n]+)",
        section,
        re.IGNORECASE,
    )
    if not row_match:
        return blocks

    name = _clean(row_match.group(1))
    address_line = _clean(row_match.group(2))
    gst = _clean(row_match.group(3) or "")
    address = address_line
    if gst:
        address = f"{address_line} ({gst})"
    extra = _clean(row_match.group(4) or "") or "N/A"

    if name and address:
        blocks.append({
            "consignee": name,
            "address": address,
            "additional_requirement": extra,
        })
    return blocks


def extract_addresses(text: str) -> list[str]:
    addresses = []
    for block in extract_consignee_blocks(text):
        if block.get("address"):
            addresses.append(block["address"])
    if addresses:
        return addresses

    for match in re.finditer(r"/Address\s*\n([^\n]+)", text, re.IGNORECASE):
        value = _clean(match.group(1))
        if value and value.lower() not in {"quantity", "additional"}:
            addresses.append(value)
    return addresses


def extract_bid_details(gem_id: str, session: requests.Session | None = None) -> dict[str, Any]:
    pdf_bytes = download_bid_pdf(gem_id, session=session)
    text = pdf_to_text(pdf_bytes)
    consignees = extract_consignee_blocks(text)
    primary = consignees[0] if consignees else {}

    return {
        "gem_id": gem_id,
        "pdf_url": PDF_URL.format(gem_id=gem_id),
        "documents_required_from_seller": extract_documents_required(text),
        "address": primary.get("address", ""),
        "additional_requirement": primary.get("additional_requirement", ""),
        "consignee": primary.get("consignee", ""),
        "consignees": consignees,
    }


def enrich_tender(tender: dict[str, Any], session: requests.Session | None = None) -> dict[str, Any]:
    gem_id = tender.get("gem_id")
    if not gem_id:
        return tender

    try:
        details = extract_bid_details(str(gem_id), session=session)
    except Exception as error:
        tender["pdf_error"] = str(error)
        tender["pdf_url"] = PDF_URL.format(gem_id=gem_id)
        return tender

    tender.update({
        "pdf_url": details["pdf_url"],
        "documents_required_from_seller": details["documents_required_from_seller"],
        "address": details["address"] or tender.get("address", ""),
        "additional_requirement": details["additional_requirement"],
        "consignee": details["consignee"],
        "consignees": details["consignees"],
    })
    return tender
