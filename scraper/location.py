import re

# Chhattisgarh districts / major cities (longer names first for matching)
CG_CITIES = [
    "Mohla-Manpur-Ambagarh Chowki",
    "Gaurela-Pendra-Marwahi",
    "Baloda Bazar",
    "Balodabazar",
    "Nava Raipur Atal Nagar",
    "Gandhi Nagar",
    "Ambagarh Chowki",
    "Rajnandgaon",
    "Mahasamund",
    "Manendragarh",
    "Chirmiri",
    "Ramanujganj",
    "Ambikapur",
    "Jagdalpur",
    "Dantewada",
    "Narayanpur",
    "Kondagaon",
    "Gariyaband",
    "Gariaband",
    "Kawardha",
    "Kabirdham",
    "Janjgir-Champa",
    "Janjgir",
    "Bilaspur",
    "Raigarh",
    "Raipur",
    "Dhamtari",
    "Balrampur",
    "Surajpur",
    "Sarguja",
    "Surguja",
    "Bemetara",
    "Mungeli",
    "Baloda",
    "Balod",
    "Bijapur",
    "Kanker",
    "Jashpur",
    "Koriya",
    "Korea",
    "Korba",
    "Durg",
    "Sukma",
    "Bhatapara",
    "Takhatpur",
    "Fingeshwar",
    "Pratappur",
    "Abhanpur",
    "Dharsiwa",
    "Antagarh",
    "Koylibeda",
    "Kharsiya",
    "Kharciha",
    "Patan",
    "Pakhanjur",
    "Parpodhi",
    "Geedam",
    "Kurud",
    "Arang",
    "Bastar",
    "Kota",
    "Kartala",
    "Tamnar",
    "Pusour",
    "Lormi",
    "Patharia",
    "Lailunga",
    "Sonhat",
    "Fingeshwar",
    "Takhatpur",
]

GENERIC_DEPARTMENTS = {
    "LAND ALLOTMENT",
    "CGMSC L",
    "EXECUTIVE ENGINEER",
    "EXECUTIVE ENGINEER, RURAL ENGINEERING SERVICES",
    "CHHATTISGARH STATE INDUSTRIAL DEVELOPMENT CORPORATION (CSIDC)",
    "CHIEF ENGINEER OFFICE",
}

DEPARTMENT_PATTERNS = [
    re.compile(r"MUNICIPAL\s+CORPORATION,?\s*([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"MUNICIPAL\s+COUNCIL,?\s*([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"NAGAR\s+PANCHAYAT\s+([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"(?:PWD\s+)?Div(?:ision)?\.?\s+No\.?\s*\d+\s+([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"(?:Vidhansabha\s+)?Div(?:ision)?\.?\s+(?:No\.?\s*\d+\s+)?([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"(?:Bridge|E/M)\s+Division\s+([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"(?:DIVISION|Division)\s+([A-Za-z][A-Za-z\s\-]+)$", re.I),
    re.compile(r"^([A-Za-z][A-Za-z\s\-]+)\s+(?:DIVISION|Division)$", re.I),
    re.compile(r",\s*([A-Z][A-Za-z\s\-]{2,})$"),
    re.compile(r"^([A-Z]{4,})$"),
]

DESCRIPTION_PATTERNS = [
    re.compile(r"DISTRICT[:\s\-–]+([A-Z][A-Z0-9\s\-]+?)(?:\s*\(C\.G\.\)|\s*,|\s+i/c|\s+RS\.|\s+in\s+|\s+for\s|$)", re.I),
    re.compile(r"District[:\s]+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s+Industrial|\s+in\s+|\s+for\s|\s+Chhattisgarh|$)", re.I),
    re.compile(r"distt[\.\s\-]+([a-zA-Z][a-zA-Z0-9\s\-]+?)(?:\s|$|,|\.)", re.I),
    re.compile(r"([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)?)\s*\(C\.G\.\)", re.I),
    re.compile(r"AT\s+([A-Z][A-Z\s]+)\s+CITY", re.I),
    re.compile(r"Municipal\s+Areas?\s+of\s+([A-Z][A-Za-z\s\-]+)", re.I),
    re.compile(r"NAGAR\s+(?:PANCHAYAT|PALIKA)\s+([A-Z][A-Za-z\s\-]+)", re.I),
    re.compile(r"Industrial\s+Area[:\s]+([A-Za-z][A-Za-z0-9\s\-]+?)(?:\s*,|\s+Sector|$)", re.I),
    re.compile(r"BLOCK[–\s\-]+([A-Z][A-Za-z0-9\s\-]+?)(?:\s*,\s*DISTRICT|\s*,|\s+DISTRICT)", re.I),
    re.compile(r"Under\s+(?:Sub\s+)?Div(?:ision)?\.?\s+[^,]+,\s*([A-Za-z][A-Za-z\s\-]+)", re.I),
    re.compile(r"(?:at|in)\s+([A-Z][A-Za-z]{3,})(?:\s*,|\s+distt|\s+district|\s+block)", re.I),
]


def _clean(value):
    if not value:
        return ""
    cleaned = re.sub(r"\s+", " ", value).strip(" -–,.")
    return cleaned.title() if cleaned.isupper() or cleaned.islower() else cleaned


def _match_known_city(text):
    if not text:
        return ""
    upper = text.upper()
    for city in CG_CITIES:
        if re.search(rf"\b{re.escape(city.upper())}\b", upper):
            return _clean(city)
    return ""


def _match_patterns(text, patterns):
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            value = _clean(match.group(1))
            if value and len(value) >= 3:
                return value
    return ""


def _from_department(department):
    dept = (department or "").strip()
    if not dept or dept.upper() in GENERIC_DEPARTMENTS:
        return ""

    city = _match_patterns(dept, DEPARTMENT_PATTERNS)
    if city:
        return city

    return _match_known_city(dept)


def _from_description(name):
    text = (name or "").strip()
    if not text:
        return ""

    city = _match_patterns(text, DESCRIPTION_PATTERNS)
    if city:
        return city

    return _match_known_city(text)


def extract_area_city(name="", department="", scraped_city=""):
    if scraped_city:
        return _clean(scraped_city)

    city = _from_department(department)
    if city:
        return city

    city = _from_description(name)
    if city:
        return city

    return _match_known_city(f"{name} {department}")
