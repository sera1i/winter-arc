import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8039"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
PYTHON_BIN = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python"
OUTPUT_DIR = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/screenshots/performance"
os.makedirs(OUTPUT_DIR, exist_ok=True)

server_process = subprocess.Popen(
    [PYTHON_BIN, "manage.py", "runserver", f"127.0.0.1:{SERVER_PORT}", "--noreload"],
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

def run_audit():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # 1. Capture Loader in action (Mobile)
            print("Capturing Loader active state...")
            context_loader = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
            page_loader = context_loader.new_page()
            page_loader.goto(f"{BASE_URL}/", wait_until="commit")
            page_loader.wait_for_timeout(120)
            page_loader.screenshot(path=os.path.join(OUTPUT_DIR, "00_loader_active.png"))
            context_loader.close()

            # 2. Profile Mobile (4x CPU slowdown)
            print("Profiling Mobile with 4x CPU throttle...")
            context_m = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
            page_m = context_m.new_page()
            client_m = page_m.context.new_cdp_session(page_m)
            client_m.send("Emulation.setCPUThrottlingRate", {"rate": 4})

            page_m.add_init_script("""
                window.__longTasks = [];
                window.__tbt = 0;
                window.__cls = 0;
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        window.__longTasks.push({
                            duration: entry.duration,
                            startTime: entry.startTime
                        });
                        if (entry.duration > 50) {
                            window.__tbt += (entry.duration - 50);
                        }
                    }
                }).observe({ entryTypes: ['longtask'] });

                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) {
                            window.__cls += entry.value;
                        }
                    }
                }).observe({ entryTypes: ['layout-shift'] });
            """)

            page_m.goto(f"{BASE_URL}/", wait_until="networkidle")
            page_m.wait_for_timeout(4500)

            m_fcp = page_m.evaluate("(() => { const e = performance.getEntriesByName('first-contentful-paint'); return e.length ? e[0].startTime : null; })()")
            m_lcp = page_m.evaluate("(() => { const e = performance.getEntriesByType('largest-contentful-paint'); return e.length ? e[e.length-1].startTime : null; })()")
            m_cls = page_m.evaluate("window.__cls")
            m_tbt = page_m.evaluate("window.__tbt")
            m_tasks = page_m.evaluate("window.__longTasks")

            # Scroll to trigger lazy images for complete visual verification screenshot
            page_m.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page_m.wait_for_timeout(600)
            page_m.evaluate("window.scrollTo(0, 0)")
            page_m.wait_for_timeout(300)
            page_m.screenshot(path=os.path.join(OUTPUT_DIR, "01_landing_mobile_full.png"), full_page=True)
            context_m.close()

            # 3. Profile Desktop (Unthrottled)
            print("Profiling Desktop unthrottled...")
            context_d = browser.new_context(viewport={"width": 1440, "height": 900})
            page_d = context_d.new_page()

            page_d.add_init_script("""
                window.__longTasks = [];
                window.__tbt = 0;
                window.__cls = 0;
                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        window.__longTasks.push({
                            duration: entry.duration,
                            startTime: entry.startTime
                        });
                        if (entry.duration > 50) {
                            window.__tbt += (entry.duration - 50);
                        }
                    }
                }).observe({ entryTypes: ['longtask'] });

                new PerformanceObserver((list) => {
                    for (const entry of list.getEntries()) {
                        if (!entry.hadRecentInput) {
                            window.__cls += entry.value;
                        }
                    }
                }).observe({ entryTypes: ['layout-shift'] });
            """)

            page_d.goto(f"{BASE_URL}/", wait_until="networkidle")
            page_d.wait_for_timeout(4500)

            d_fcp = page_d.evaluate("(() => { const e = performance.getEntriesByName('first-contentful-paint'); return e.length ? e[0].startTime : null; })()")
            d_lcp = page_d.evaluate("(() => { const e = performance.getEntriesByType('largest-contentful-paint'); return e.length ? e[e.length-1].startTime : null; })()")
            d_cls = page_d.evaluate("window.__cls")
            d_tbt = page_d.evaluate("window.__tbt")
            d_tasks = page_d.evaluate("window.__longTasks")

            page_d.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page_d.wait_for_timeout(600)
            page_d.evaluate("window.scrollTo(0, 0)")
            page_d.wait_for_timeout(300)
            page_d.screenshot(path=os.path.join(OUTPUT_DIR, "02_landing_desktop_full.png"), full_page=True)
            context_d.close()

            browser.close()

            print("\n================ FINAL VERIFICATION METRICS ================")
            print(f"MOBILE (4x CPU Throttling):")
            print(f"  FCP:        {m_fcp:.1f} ms" if m_fcp else "  FCP:        N/A")
            print(f"  LCP:        {m_lcp:.1f} ms" if m_lcp else "  LCP:        N/A")
            print(f"  CLS:        {m_cls:.4f}")
            print(f"  TBT:        {m_tbt:.1f} ms")
            print(f"  Long Tasks: {len(m_tasks)} tasks -> {[round(t['duration'], 1) for t in m_tasks]}")
            print(f"\nDESKTOP (Unthrottled):")
            print(f"  FCP:        {d_fcp:.1f} ms" if d_fcp else "  FCP:        N/A")
            print(f"  LCP:        {d_lcp:.1f} ms" if d_lcp else "  LCP:        N/A")
            print(f"  CLS:        {d_cls:.4f}")
            print(f"  TBT:        {d_tbt:.1f} ms")
            print(f"  Long Tasks: {len(d_tasks)} tasks -> {[round(t['duration'], 1) for t in d_tasks]}")
            print("============================================================\n")

    finally:
        server_process.terminate()
        server_process.wait()

if __name__ == "__main__":
    run_audit()
