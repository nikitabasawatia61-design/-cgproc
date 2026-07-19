import io
import re

import requests

try:
    import pypdf
except ImportError:
    pypdf = None

try:
    import pdfplumber
except ImportError:
    pdfplumber = None

gem_id = "9622895"
url = f"https://bidplus.gem.gov.in/showbidDocument/{gem_id}"
s = requests.Session()
s.headers.update({"User-Agent": "Mozilla/5.0", "Referer": "https://bidplus.gem.gov.in/"})
r = s.get(url, timeout=60)
print("pdf status", r.status_code, "bytes", len(r.content))
data = r.content

text = ""
if pypdf:
    reader = pypdf.PdfReader(io.BytesIO(data))
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
elif pdfplumber:
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"
else:
    print("install pypdf or pdfplumber")
    raise SystemExit(1)

print("text len", len(text))
print("--- sample ---")
print(text[:4000])

for label in [
    "Document required",
    "Document Required",
    "from seller",
    "Address",
    "AddreAddress",
    "Additional Address",
    "Delivery Address",
    "Consignee",
]:
    idx = text.lower().find(label.lower())
    if idx >= 0:
        print(f"\n=== {label} context ===")
        print(text[max(0, idx - 50) : idx + 400])
