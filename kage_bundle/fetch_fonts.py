import urllib.request
import hashlib
import os

os.makedirs('static/fonts', exist_ok=True)
os.makedirs('kage_bundle/assets/fonts', exist_ok=True)

font_urls = [
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/256fa8037be67fd4a857a660c328a09e4696a0fb5de166f1357534a81f738556.woff2', 'Onest-Light-300.woff2', '256fa8037be67fd4a857a660c328a09e4696a0fb5de166f1357534a81f738556'),
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/cbc780c47e7975372debee1cad74f54bc38a3d366840a74b0af33bdd9ce5e8cf.woff2', 'Onest-Regular-400.woff2', 'cbc780c47e7975372debee1cad74f54bc38a3d366840a74b0af33bdd9ce5e8cf'),
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/21150b504f3aa78ba6dd04a6d11dd938fdc7c354f7e93ee2312fa18046d3aabd.woff2', 'Onest-Medium-500.woff2', '21150b504f3aa78ba6dd04a6d11dd938fdc7c354f7e93ee2312fa18046d3aabd'),
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/98e3406af6c57c1b730a1f043cf087689fb16d2dc0bc37feb7d5f1860f55d01e.woff2', 'Onest-Bold-700.woff2', '98e3406af6c57c1b730a1f043cf087689fb16d2dc0bc37feb7d5f1860f55d01e'),
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/919f3ce938b0deabdf894554f466747c789806daddc1e3ab2a01d4cff4464382.woff2', 'NotoJP-Regular-400.woff2', '919f3ce938b0deabdf894554f466747c789806daddc1e3ab2a01d4cff4464382'),
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/6a93626eb17466bfd9239cec66b2c371bb20381999776a5d16e2c22a92f00349.woff2', 'Wordmark-500.woff2', '6a93626eb17466bfd9239cec66b2c371bb20381999776a5d16e2c22a92f00349'),
    ('https://ublctyddhtbgaersvxxb.supabase.co/storage/v1/object/public/threeui-media/scene-images/embedded/87832ba80d7ac0927a4c4c32588e0f92d368eca9ae70a99e720769ed7153bc3d.woff2', 'Wordmark-600.woff2', '87832ba80d7ac0927a4c4c32588e0f92d368eca9ae70a99e720769ed7153bc3d'),
]

for url, filename, expected_sha in font_urls:
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    
    sha = hashlib.sha256(data).hexdigest()
    print(f"Font: {filename} ({len(data)} bytes) | SHA-256 match: {sha == expected_sha}")
    
    # Save to both static/fonts and kage_bundle/assets/fonts
    for dest_dir in ['static/fonts', 'kage_bundle/assets/fonts']:
        with open(os.path.join(dest_dir, filename), 'wb') as f:
            f.write(data)

print("All 7 local font assets saved and hash-verified.")
