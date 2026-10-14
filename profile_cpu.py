import json
import time
import subprocess
import urllib.request
import sys
from playwright.sync_api import sync_playwright

SERVER_PORT = "8035"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
python_bin = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python"

server_process = subprocess.Popen(
    [python_bin, "manage.py", "runserver", f"127.0.0.1:{SERVER_PORT}", "--noreload"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

ready = False
for _ in range(40):
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=1) as resp:
            if resp.status == 200:
                ready = True
                break
    except Exception:
        time.sleep(0.5)

if not ready:
    server_process.kill()
    sys.exit(1)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        page = context.new_page()
        
        client = page.context.new_cdp_session(page)
        client.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        client.send("Profiler.enable")
        client.send("Profiler.start")

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(4000)

        profile_res = client.send("Profiler.stop")
        profile = profile_res.get("profile", {})
        
        # Analyze top CPU functions
        nodes = profile.get("nodes", [])
        samples = profile.get("samples", [])
        time_deltas = profile.get("timeDeltas", [])
        
        node_map = {n["id"]: n for n in nodes}
        node_time = {}
        for sample_id, delta in zip(samples, time_deltas):
            node_time[sample_id] = node_time.get(sample_id, 0) + delta

        results = []
        for nid, micros in node_time.items():
            node = node_map.get(nid, {})
            call_frame = node.get("callFrame", {})
            fn_name = call_frame.get("functionName", "(anonymous)")
            url = call_frame.get("url", "")
            line = call_frame.get("lineNumber", -1)
            results.append((micros / 1000.0, fn_name, url, line))

        results.sort(key=lambda x: x[0], reverse=True)
        print("=== TOP CPU TIME FUNCTIONS (ms) ===")
        for ms, fn, url, line in results[:25]:
            short_url = url.split("/")[-1] if url else ""
            print(f"  {ms:8.2f} ms | {fn:30} | {short_url}:{line}")

        context.close()
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
