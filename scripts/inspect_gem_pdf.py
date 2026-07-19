import re

import requests

gem_id = "9622895"
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://bidplus.gem.gov.in/"})
r = s.get(f"https://bidplus.gem.gov.in/showbidresult/{gem_id}", timeout=30)
print("status", r.status_code, "len", len(r.text))
links = re.findall(r'href=["\']([^"\']+)["\']', r.text)
for link in links:
    low = link.lower()
    if any(k in low for k in ("pdf", "download", "document", "bid", "print")):
        print("LINK:", link[:120])

# try common GeM PDF endpoints
candidates = [
    f"https://bidplus.gem.gov.in/showbidDocument/{gem_id}",
    f"https://bidplus.gem.gov.in/bidding/bid/getBidDocument/{gem_id}",
    f"https://bidplus.gem.gov.in/showbidresult/downloadBidDocument/{gem_id}",
]
for url in candidates:
    try:
        rr = s.head(url, timeout=15, allow_redirects=True)
        print("HEAD", url, rr.status_code, rr.headers.get("content-type"))
    except Exception as e:
        print("HEAD fail", url, e)
