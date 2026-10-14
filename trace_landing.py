import json
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8027"
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
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        
        # Start CDP trace
        client = page.context.new_cdp_session(page)
        client.send("Tracing.start", {
            "categories": "devtools.timeline,disabled-by-default-devtools.timeline,v8.execute,blink.user_timing",
            "options": "sampling-frequency=10000"
        })

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(4000)

        trace_data = []
        def on_trace_data(params):
            trace_data.extend(params.get("value", []))

        client.on("Tracing.dataCollected", on_trace_data)
        client.send("Tracing.end")
        
        # Wait for trace completion
        time.sleep(1)

        print(f"Collected {len(trace_data)} trace events.")
        
        # Analyze long events
        long_events = []
        for ev in trace_data:
            dur = ev.get("dur", 0) / 1000.0 # ms
            name = ev.get("name", "")
            if dur > 50:
                args = ev.get("args", {})
                long_events.append((dur, name, args))

        long_events.sort(key=lambda x: x[0], reverse=True)
        print("Top 15 Longest Trace Events (>50ms):")
        for dur, name, args in long_events[:15]:
            print(f"  {dur:.2f} ms: {name} - {json.dumps(args)[:120]}")

        context.close()
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
