"""Fetch open bids from GeM BidPlus advance search (state/city filter)."""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import requests

BASE_URL = "https://bidplus.gem.gov.in"
ADVANCE_SEARCH_URL = f"{BASE_URL}/advance-search"
SEARCH_BIDS_URL = f"{BASE_URL}/search-bids"
STATE_LIST_URL = f"{BASE_URL}/state-list-adv"
CITY_LIST_URL = f"{BASE_URL}/city-list-adv"

DEFAULT_STATE = "CHHATTISGARH"
DEFAULT_CITY = "KORBA"
PAGE_SIZE = 10

IST = timezone(timedelta(hours=5, minutes=30))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": BASE_URL,
    "Referer": ADVANCE_SEARCH_URL,
    "X-Requested-With": "XMLHttpRequest",
}


def _first(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value)


def _format_end_date(iso_value: str) -> str:
    if not iso_value:
        return ""
    cleaned = iso_value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(cleaned)
    except ValueError:
        return iso_value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    local = parsed.astimezone(IST)
    return local.strftime("%d %b, %Y %I:%M:%S %p IST")


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(HEADERS)
    return session


def fetch_csrf(session: requests.Session) -> str:
    response = session.get(ADVANCE_SEARCH_URL, timeout=30)
    response.raise_for_status()

    csrf = session.cookies.get("csrf_gem_cookie")
    if csrf:
        return csrf

    match = re.search(r'name="csrf_bd_gem_nk"\s+value="([^"]+)"', response.text)
    if match:
        return match.group(1)

    raise RuntimeError("Could not obtain GeM CSRF token")


def fetch_states(session: requests.Session | None = None) -> list[dict[str, str]]:
    session = session or create_session()
    csrf = fetch_csrf(session)
    response = session.post(STATE_LIST_URL, data={"csrf_bd_gem_nk": csrf}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return payload.get("data") or []


def fetch_cities(
    state_name: str,
    session: requests.Session | None = None,
) -> list[dict[str, str]]:
    session = session or create_session()
    csrf = fetch_csrf(session)
    response = session.post(
        CITY_LIST_URL,
        data={"state_name": state_name, "csrf_bd_gem_nk": csrf},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload.get("data") or []


def search_bids_page(
    session: requests.Session,
    csrf: str,
    *,
    state_name: str,
    city_name: str,
    page: int,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "searchType": "con",
            "state_name_con": state_name,
            "city_name_con": city_name,
            "bidEndFromCon": "",
            "bidEndToCon": "",
            "page": page,
        }
    )
    response = session.post(
        SEARCH_BIDS_URL,
        data={"payload": payload, "csrf_bd_gem_nk": csrf},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != 1:
        message = data.get("message") or "GeM search failed"
        raise RuntimeError(message)
    return data["response"]["response"]


def normalize_bid(doc: dict[str, Any], *, city_name: str) -> dict[str, str]:
    gem_id = _first(doc.get("id"))
    bid_number = _first(doc.get("b_bid_number"))
    title = _first(doc.get("bbt_title")) or _first(doc.get("b_category_name"))
    ministry = _first(doc.get("ba_official_details_minName"))
    department = _first(doc.get("ba_official_details_deptName"))
    if ministry and department:
        department = f"{department} · {ministry}"
    elif ministry:
        department = ministry

    end_iso = _first(doc.get("final_end_date_sort"))
    now = datetime.now().isoformat(timespec="seconds")

    return {
        "tender_no": bid_number or gem_id,
        "name": title,
        "department": department,
        "amount": "",
        "last_date": _format_end_date(end_iso),
        "area_city": city_name or DEFAULT_CITY,
        "first_seen_at": now,
        "last_updated_at": now,
        "gem_id": gem_id,
        "url": f"{BASE_URL}/showbidresult/{gem_id}" if gem_id else "",
        "source": "gem",
    }


def fetch_gem_tenders(
    *,
    state_name: str = DEFAULT_STATE,
    city_name: str = DEFAULT_CITY,
) -> list[dict[str, str]]:
    session = create_session()
    csrf = fetch_csrf(session)

    first_page = search_bids_page(
        session,
        csrf,
        state_name=state_name,
        city_name=city_name,
        page=1,
    )
    total = int(first_page.get("numFound") or 0)
    docs = list(first_page.get("docs") or [])

    if total > PAGE_SIZE:
        pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
        for page in range(2, pages + 1):
            page_data = search_bids_page(
                session,
                csrf,
                state_name=state_name,
                city_name=city_name,
                page=page,
            )
            docs.extend(page_data.get("docs") or [])

    return [normalize_bid(doc, city_name=city_name) for doc in docs]
