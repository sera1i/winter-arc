import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8026"
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
    print("Server failed to start")
    server_process.kill()
    sys.exit(1)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Test Mobile Viewport with CPU Throttling (Simulate 4x slowdown like Lighthouse)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True
        )
        page = context.new_page()
        client = page.context.new_cdp_session(page)
        client.send("Emulation.setCPUThrottlingRate", {"rate": 4})
        
        # Collect long tasks
        page.add_init_script("""
            window.__longTasks = [];
            window.__tbt = 0;
            const observer = new PerformanceObserver((list) => {
                for (const entry of list.getEntries()) {
                    window.__longTasks.push({
                        name: entry.name,
                        startTime: entry.startTime,
                        duration: entry.duration,
                        attribution: entry.attribution ? entry.attribution.map(a => a.name || a.containerSrc || a.containerType) : []
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
        # Wait 5 seconds to observe settling and any long tasks
        page.wait_for_timeout(5000)
        total_time = time.time() - t0

        long_tasks = page.evaluate("window.__longTasks")
        tbt = page.evaluate("window.__tbt")
        
        fcp = page.evaluate("""
            (() => {
                const paint = performance.getEntriesByType('paint');
                const fcpEntry = paint.find(p => p.name === 'first-contentful-paint');
                return fcpEntry ? fcpEntry.startTime : null;
            })()
        """)
        
        lcp = page.evaluate("""
            (() => {
                const entries = performance.getEntriesByType('largest-contentful-paint');
                return entries.length > 0 ? entries[entries.length - 1].startTime : null;
            })()
        """)

        print(f"=== MOBILE PROFILING RESULTS (4x CPU Throttling) ===")
        print(f"FCP: {fcp:.2f} ms" if fcp else "FCP: N/A")
        print(f"LCP: {lcp:.2f} ms" if lcp else "LCP: N/A")
        print(f"Total Blocking Time (TBT): {tbt:.2f} ms")
        print(f"Number of Long Tasks (>50ms): {len(long_tasks)}")
        for i, task in enumerate(long_tasks[:15]):
            print(f"  Task {i+1}: {task['duration']:.2f} ms at {task['startTime']:.2f} ms - attr: {task['attribution']}")

        context.close()
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
