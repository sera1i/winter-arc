import urllib.request
import hashlib
import os

os.makedirs('kage_bundle/assets', exist_ok=True)

assets = [
    ('https://threeui.com/landing-pages/secret-pathways-assets/fonts.css', 'fonts.css', 99356, '985f85a904a4096f92c06552b06f42a45973ac004af4780d68f18af65ddcc1b0'),
    ('https://threeui.com/landing-pages/secret-pathways-assets/three.min.js', 'three.min.js', 608081, '8a5f7249903b54d30f79f708699d2fed2d6a1d0741a4cd41377d1f01bb5a2271'),
]

for url, filename, expected_bytes, expected_sha in assets:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            content = resp.read()
        target = os.path.join('kage_bundle/assets', filename)
        with open(target, 'wb') as f:
            f.write(content)
        actual_bytes = len(content)
        actual_sha = hashlib.sha256(content).hexdigest()
        print(f"Downloaded {filename}:")
        print(f"  Bytes: {actual_bytes} (Expected: {expected_bytes}) -> Match: {actual_bytes == expected_bytes}")
        print(f"  SHA-256: {actual_sha}")
        print(f"  Expected: {expected_sha} -> Match: {actual_sha == expected_sha}")
    except Exception as e:
        print(f"Failed {filename}: {e}")
