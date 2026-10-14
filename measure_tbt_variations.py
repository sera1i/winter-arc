import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8029"
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

def measure(cpu_rate=4, block_three=False, is_mobile=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        viewport = {"width": 390, "height": 844} if is_mobile else {"width": 1440, "height": 900}
        context = browser.new_context(viewport=viewport, is_mobile=is_mobile)
        page = context.new_page()

        if block_three:
            page.route("**/three*.js", lambda route: route.abort())

        client = page.context.new_cdp_session(page)
        if cpu_rate > 1:
            client.send("Emulation.setCPUThrottlingRate", {"rate": cpu_rate})

        page.add_init_script("""
            window.__longTasks = [];
            window.__tbt = 0;
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window.__longTasks.push({
                        name: entry.name,
                        startTime: entry.startTime,
                        duration: entry.duration
                    });
                    if (entry.duration > 50) {
                        window.__tbt += (entry.duration - 50);
                    }
                }
            });
            observer.observe({ entryTypes: ['longtask'] });
        """)

        t0 = time.time()
        page.goto(f"{BASE_URL}/", wait_until="networkidle")
        page.wait_for_timeout(6000)

        tbt = page.evaluate("window.__tbt")
        tasks = page.evaluate("window.__longTasks")
        context.close()
        browser.close()
        return tbt, len(tasks), [round(t['duration'], 1) for t in tasks]

try:
    print("Measuring Baseline Mobile (4x CPU)...")
    tbt_m, count_m, tasks_m = measure(cpu_rate=4, block_three=False, is_mobile=True)
    print(f"  Mobile TBT: {tbt_m:.1f} ms | Long tasks ({count_m}): {tasks_m}")

    print("Measuring Mobile WITHOUT Three.js (4x CPU)...")
    tbt_no3, count_no3, tasks_no3 = measure(cpu_rate=4, block_three=True, is_mobile=True)
    print(f"  Mobile No-Three TBT: {tbt_no3:.1f} ms | Long tasks ({count_no3}): {tasks_no3}")

    print("Measuring Desktop (No Throttling)...")
    tbt_d, count_d, tasks_d = measure(cpu_rate=1, block_three=False, is_mobile=False)
    print(f"  Desktop TBT: {tbt_d:.1f} ms | Long tasks ({count_d}): {tasks_d}")
finally:
    server_process.terminate()
    server_process.wait()
