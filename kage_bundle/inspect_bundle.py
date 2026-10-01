import json
import hashlib
import os

with open('kage_bundle/kage-landing-page.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total files in bundle: {len(data['files'])}")
for idx, file_obj in enumerate(data['files']):
    p = file_obj.get("path")
    b = file_obj.get("bytes")
    sha = file_obj.get("sha256")
    code = file_obj.get("code")
    print(f"File {idx+1}: {p}")
    print(f"  Role: {file_obj.get('role')}")
    print(f"  Declared Bytes: {b} | Declared SHA-256: {sha}")
    if code is not None:
        code_bytes = code.encode('utf-8')
        actual_len = len(code_bytes)
        actual_sha = hashlib.sha256(code_bytes).hexdigest()
        print(f"  Actual String Bytes: {actual_len} | Actual SHA-256: {actual_sha}")
        # Extract file to kage_bundle/extracted/
        target_path = os.path.join('kage_bundle', 'extracted', p)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'w', encoding='utf-8') as out_f:
            out_f.write(code)
    else:
        print("  Code: None / binary asset")

print("\nAll bundle files extracted to kage_bundle/extracted/")
