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


def _is_stop_footer(line: str) -> bool:
    low = line.lower()
    markers = (
        "buyer added",
        "option clause",
        "number of covers",
        "checklist of the documents",
        "generic",
        "जोड़",
    )
    return any(marker in low for marker in markers)


def _is_quantity_line(line: str) -> bool:
    return bool(re.fullmatch(r"\d+", line))


def _is_address_start(line: str) -> bool:
    return bool(re.match(r"^\d{6},", line))


def _is_gst_line(line: str) -> bool:
    return bool(re.match(r"^\(GST-", line, re.IGNORECASE))


def _continues_address(line: str) -> bool:
    if not line or _is_stop_footer(line):
        return False
    if _is_quantity_line(line):
        return False
    if line.upper() in {"N/A", "PROJECT /", "LUMPSUM", "BASED"}:
        return False
    if re.match(r"^(Project|Lumpsum|Based)\s*/?\s*$", line, re.IGNORECASE):
        return False
    return bool(re.search(r"[A-Za-z]", line))


def _parse_consignee_row(lines: list[str]) -> dict[str, str] | None:
    if not lines:
        return None

    addr_start = next((i for i, line in enumerate(lines) if _is_address_start(line)), None)
    if addr_start is None:
        return None

    name = _clean(" ".join(lines[:addr_start]))
    address_parts: list[str] = []
    extra = "N/A"

    for line in lines[addr_start:]:
        if _is_stop_footer(line):
            break
        if address_parts and _is_quantity_line(line):
            break
        if address_parts and line.upper() == "N/A":
            extra = "N/A"
            break
        if _is_address_start(line) or _is_gst_line(line) or (address_parts and _continues_address(line)):
            address_parts.append(line)
            continue
        if address_parts:
            if not re.match(r"^(Project|Lumpsum|Based)\s*/?\s*$", line, re.IGNORECASE):
                extra = _clean(line) or extra
            break

    address = _clean(" ".join(address_parts))
    if not name or not address:
        return None

    return {
        "consignee": name,
        "address": address,
        "additional_requirement": extra or "N/A",
    }


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
    row_match = re.search(r"(?:^|\n)1\n(.+)", section, re.DOTALL)
    if not row_match:
        return blocks

    raw_lines = [line.strip() for line in row_match.group(1).split("\n") if line.strip()]
    cleaned_lines: list[str] = []
    for line in raw_lines:
        if cleaned_lines and _is_stop_footer(line):
            break
        cleaned_lines.append(line)

    parsed = _parse_consignee_row(cleaned_lines)
    if parsed:
        blocks.append(parsed)
        return blocks

    # Legacy layout: single-line name, address, GST in parentheses.
    legacy_match = re.search(
        r"\n1\s*\n([^\n]+)\n([^\n]+)\n\(([^\)]+)\)\s*\n"
        r"(?:Project\s*/\s*\n)?(?:Lumpsum\s*\n)?(?:Based\s*\n)?"
        r"(N/A|[^\n]+)",
        section,
        re.IGNORECASE,
    )
    if legacy_match:
        name = _clean(legacy_match.group(1))
        address_line = _clean(legacy_match.group(2))
        gst = _clean(legacy_match.group(3) or "")
        address = f"{address_line} ({gst})" if gst else address_line
        extra = _clean(legacy_match.group(4) or "") or "N/A"
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
