import subprocess
import urllib.request
import time
from playwright.sync_api import sync_playwright

SERVER_PORT = "8030"
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
    exit(1)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        page = context.new_page()
        page.route("**/three*.js", lambda route: route.abort())

        client = page.context.new_cdp_session(page)
        client.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        client.send("Profiler.enable")
        client.send("Profiler.start")

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(3000)

        profile_res = client.send("Profiler.stop")
        profile = profile_res.get("profile", {})
        
        nodes = profile.get("nodes", [])
        samples = profile.get("samples", [])
        time_deltas = profile.get("timeDeltas", [])
        node_map = {n["id"]: n for n in nodes}
        node_time = {}
        for s_id, dt in zip(samples, time_deltas):
            node_time[s_id] = node_time.get(s_id, 0) + dt

        results = []
        for nid, micros in node_time.items():
            n = node_map.get(nid, {})
            cf = n.get("callFrame", {})
            results.append((micros / 1000.0, cf.get("functionName"), cf.get("url"), cf.get("lineNumber")))

        results.sort(key=lambda x: x[0], reverse=True)
        print("=== NON-THREE CPU FUNCTIONS ===")
        for ms, fn, url, line in results[:20]:
            print(f"  {ms:8.2f} ms | {fn:25} | {url}:{line}")

        context.close()
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
