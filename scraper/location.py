import re


DISTRICT_PATTERNS = [
    re.compile(r"DISTRICT[:\s\-–]+([A-Z][A-Z0-9\s\-]+?)(?:\s*\(C\.G\.\)|\s*,|\s+i/c|\s+RS\.|\s+in\s+|\s+for\s|$)", re.I),
    re.compile(r"District[:\s]+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s+Industrial|\s+in\s+|\s+for\s|\s+Chhattisgarh|$)", re.I),
    re.compile(r"distt[\.\s\-]+([a-zA-Z][a-zA-Z0-9\s\-]+?)(?:\s|$|,|\.)", re.I),
]

CITY_PATTERNS = [
    re.compile(r"AT\s+([A-Z][A-Z\s]+)\s+CITY", re.I),
    re.compile(r"Municipal Areas of\s+([A-Z][A-Z\s\-]+)", re.I),
    re.compile(r"NAGAR\s+(?:PANCHAYAT|PALIKA)\s+([A-Z][A-Z\s\-]+)", re.I),
    re.compile(r"Industrial Area[:\s]+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s+Sector|$)", re.I),
    re.compile(r"BLOCK[–\s\-]+([A-Z][A-Z0-9\s\-]+?)(?:\s*,\s*DISTRICT|\s*,|\s+DISTRICT)", re.I),
]


def _clean(value):
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip(" -–,")
    return cleaned


def extract_area_city(name="", department="", scraped_city=""):
    if scraped_city:
        return _clean(scraped_city)

    text = f"{name} {department}".strip()
    if not text:
        return ""

    for pattern in DISTRICT_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean(match.group(1))

    for pattern in CITY_PATTERNS:
        match = pattern.search(text)
        if match:
            return _clean(match.group(1))

    return ""
