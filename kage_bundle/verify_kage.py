import urllib.request
import json
import hashlib
import os

os.makedirs('kage_bundle', exist_ok=True)

# 1. Fetch JSON
url_json = 'https://threeui.com/source-code/kage-landing-page.json'
req_json = urllib.request.Request(url_json, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_json) as resp:
    raw_json = resp.read()
    data = json.loads(raw_json.decode('utf-8'))

with open('kage_bundle/kage-landing-page.json', 'wb') as f:
    f.write(raw_json)

print("=== KAGE SOURCE BUNDLE INSPECTION ===")
print("Schema Version:", data.get("schemaVersion"))
print("ID:", data.get("id"))
print("Total Files:", len(data.get("files", [])))

for i, f in enumerate(data.get("files", [])):
    p = f.get("path")
    b = f.get("bytes")
    sha = f.get("sha256")
    code = f.get("code", "")
    computed_sha = hashlib.sha256(code.encode('utf-8')).hexdigest() if code else None
    print(f"[{i+1}] {p} | {b} bytes | SHA-256 match: {computed_sha == sha}")

# 2. Fetch standalone kage.html
url_html = 'https://threeui.com/landing-pages/kage.html'
req_html = urllib.request.Request(url_html, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_html) as resp:
    raw_html = resp.read()

with open('kage_bundle/kage.html', 'wb') as f:
    f.write(raw_html)

html_sha = hashlib.sha256(raw_html).hexdigest()
print(f"Saved kage.html | {len(raw_html)} bytes | SHA-256: {html_sha}")
