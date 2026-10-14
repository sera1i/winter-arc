import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8031"
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
        # Abort three.js to isolate the non-three culprits first
        page.route("**/three*.js", lambda route: route.abort())

        client = page.context.new_cdp_session(page)
        client.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        client.send("Performance.enable")

        page.add_init_script("""
            window.__timeline = [];
            const mark = (label) => {
                window.__timeline.push({ label, time: performance.now() });
            };
            mark('init_start');
            document.addEventListener('DOMContentLoaded', () => mark('DOMContentLoaded'));
            window.addEventListener('load', () => mark('window_load'));

            const obs = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window.__timeline.push({
                        type: 'longtask',
                        startTime: entry.startTime,
                        duration: entry.duration,
                        attribution: entry.attribution.map(a => ({
                            name: a.name,
                            containerSrc: a.containerSrc,
                            containerType: a.containerType
                        }))
                    });
                }
            });
            obs.observe({ entryTypes: ['longtask'] });
        """)

        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(4000)

        timeline = page.evaluate("window.__timeline")
        print("=== TIMELINE OF EVENTS AND LONG TASKS ===")
        for item in timeline:
            if item.get("type") == "longtask":
                print(f"  [LONGTASK] {item['duration']:.1f}ms starting at {item['startTime']:.1f}ms: {item['attribution']}")
            else:
                print(f"  [MARK] {item['label']} at {item['time']:.1f}ms")

        context.close()
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
