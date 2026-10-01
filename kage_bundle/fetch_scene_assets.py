import re
import urllib.request
import hashlib
import os

with open('kage_bundle/kage.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all external/binary URLs referenced in kage.html
urls = re.findall(r'https://ublctyddhtbgaersvxxb\.supabase\.co/storage/v1/object/public/threeui-media/scene-images/[^\s\'"\)\>]+', content)
unique_urls = sorted(list(set(urls)))

print(f"Total referenced scene images/textures in kage.html: {len(unique_urls)}")
os.makedirs('static/kage/scene-images', exist_ok=True)
os.makedirs('kage_bundle/assets/scene-images', exist_ok=True)

manifest = []
for idx, url in enumerate(unique_urls):
    filename = url.split('/')[-1]
    # Download
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        sha = hashlib.sha256(data).hexdigest()
        size = len(data)
        print(f"[{idx+1}/{len(unique_urls)}] {filename} | {size} bytes | SHA-256: {sha}")
        manifest.append({
            'url': url,
            'filename': filename,
            'size': size,
            'sha256': sha
        })
        for target_dir in ['static/kage/scene-images', 'kage_bundle/assets/scene-images']:
            with open(os.path.join(target_dir, filename), 'wb') as out_f:
                out_f.write(data)
    except Exception as e:
        print(f"Error downloading {url}: {e}")

with open('kage_bundle/assets/manifest.json', 'w', encoding='utf-8') as f:
    import json
    json.dump(manifest, f, indent=2)

print("\nAll scene assets downloaded and manifest generated.")
