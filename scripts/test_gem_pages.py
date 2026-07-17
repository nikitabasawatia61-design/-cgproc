import json

import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://bidplus.gem.gov.in/advance-search",
    "Origin": "https://bidplus.gem.gov.in",
})
session.get("https://bidplus.gem.gov.in/advance-search", timeout=30)
csrf = session.cookies.get("csrf_gem_cookie")

for page in (1, 2, 7):
    payload = json.dumps({
        "searchType": "con",
        "state_name_con": "CHHATTISGARH",
        "city_name_con": "KORBA",
        "bidEndFromCon": "",
        "bidEndToCon": "",
        "page": page,
    })
    r = session.post(
        "https://bidplus.gem.gov.in/search-bids",
        data={"payload": payload, "csrf_bd_gem_nk": csrf},
        timeout=30,
    )
    resp = r.json()["response"]["response"]
    print(f"page {page}: start={resp['start']} docs={len(resp['docs'])}")
