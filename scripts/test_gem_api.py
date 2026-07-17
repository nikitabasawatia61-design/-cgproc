import json
import re

import requests

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://bidplus.gem.gov.in/advance-search",
    "Origin": "https://bidplus.gem.gov.in",
})

r = session.get("https://bidplus.gem.gov.in/advance-search", timeout=30)
print("advance-search", r.status_code)
csrf = session.cookies.get("csrf_gem_cookie")
if not csrf:
    match = re.search(r'name="csrf_bd_gem_nk"\s+value="([^"]+)"', r.text)
    csrf = match.group(1) if match else None
print("csrf", csrf)

rs = session.post(
    "https://bidplus.gem.gov.in/state-list-adv",
    data={"csrf_bd_gem_nk": csrf},
    timeout=30,
)
print("states", rs.status_code, rs.text[:200])

rc = session.post(
    "https://bidplus.gem.gov.in/city-list-adv",
    data={"state_name": "CHHATTISGARH", "csrf_bd_gem_nk": csrf},
    timeout=30,
)
print("cities", rc.status_code, rc.text[:300])

payload = json.dumps({
    "searchType": "con",
    "state_name_con": "CHHATTISGARH",
    "city_name_con": "KORBA",
    "bidEndFromCon": "",
    "bidEndToCon": "",
    "page": 1,
})
rb = session.post(
    "https://bidplus.gem.gov.in/search-bids",
    data={"payload": payload, "csrf_bd_gem_nk": csrf},
    timeout=30,
)
print("bids", rb.status_code)
data = rb.json()
resp = data["response"]["response"]
print("numFound", resp["numFound"])
print("keys", sorted(resp["docs"][0].keys()))
print(json.dumps(resp["docs"][0], indent=2)[:4000])
