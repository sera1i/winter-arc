import os
import sys
import time
import json
import subprocess
import urllib.request
import re

EXTRA_LIB = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/usr/lib/x86_64-linux-gnu"
curr_ld = os.environ.get("LD_LIBRARY_PATH", "")
if EXTRA_LIB not in curr_ld:
    os.environ["LD_LIBRARY_PATH"] = f"{EXTRA_LIB}:{curr_ld}" if curr_ld else EXTRA_LIB

PY = sys.executable
BASE_URL = 'http://127.0.0.1:8000'

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status in (200, 302):
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def run_baseline_audit():
    print("=" * 75)
    print("WINTER ARC - PHASE 1: MOBILE PERFORMANCE & INTERACTION LATENCY AUDIT")
    print("=" * 75)

    # 1. Ensure fixtures
    print("[1/4] Preparing test fixtures in database...")
    subprocess.run([PY, "prepare_browser_fixtures.py"], check=True)

    # 2. Ensure server is running
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Starting Django development server...")
        server_process = subprocess.Popen(
            [PY, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=30):
            if server_process:
                server_process.kill()
            raise RuntimeError("Could not connect to Django server at 127.0.0.1:8000")
        print("Server running on 127.0.0.1:8000!")
    else:
        print("Django server is already active.")

    from playwright.sync_api import sync_playwright

    results = {
        "device": "Mobile Viewport (iPhone 14/15 390x844, 3x DPR, Touch)",
        "throttling": "Mobile 4G (Latency 70ms, Download 4Mbps, Upload 2Mbps) + 4x CPU Throttling",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "journeys": {}
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # Mobile Context: 390x844, DPR 3, touch enabled, iOS WebKit user agent
            context = browser.new_context(
                viewport={"width": 390, "height": 844},
                device_scale_factor=3,
                is_mobile=True,
                has_touch=True,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            )
            page = context.new_page()

            # Enable CDP session for realistic Mobile CPU & Network throttling
            cdp = context.new_cdp_session(page)
            # 4x CPU slowdown (representative mid-tier mobile)
            cdp.send("Emulation.setCPUThrottlingRate", {"rate": 4})
            # Mobile 4G network emulation
            cdp.send("Network.emulateNetworkConditions", {
                "offline": False,
                "downloadThroughput": int(4 * 1024 * 1024 / 8),
                "uploadThroughput": int(2 * 1024 * 1024 / 8),
                "latency": 70
            })

            requests_log = []
            def on_request(req):
                requests_log.append({
                    "url": req.url,
                    "method": req.method,
                    "resource_type": req.resource_type,
                    "start": time.time()
                })
            def on_response(res):
                # track response
                pass

            page.on("request", on_request)

            def get_nav_metrics():
                perf = page.evaluate("""() => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    if (!nav) return null;
                    return {
                        ttfb: Math.round(nav.responseStart - nav.requestStart),
                        server_response_time: Math.round(nav.responseEnd - nav.requestStart),
                        dom_interactive: Math.round(nav.domInteractive - nav.startTime),
                        dom_complete: Math.round(nav.domComplete - nav.startTime),
                        load_event: Math.round(nav.loadEventEnd - nav.startTime),
                        js_execution_rendering: Math.round(nav.domComplete - nav.responseEnd),
                        encoded_body_size: nav.encodedBodySize || 0,
                        transfer_size: nav.transferSize || 0
                    };
                }""")
                return perf

            # -------------------------------------------------------------
            # Journey 1: Initial landing-page load
            # -------------------------------------------------------------
            print("\n[Journey 1/9] Measuring Initial Landing-Page Load...")
            requests_log.clear()
            t0 = time.time()
            res = page.goto(f"{BASE_URL}/", wait_until="load", timeout=30000)
            t_interactive = page.evaluate("() => performance.timing.domInteractive - performance.timing.navigationStart")
            total_time = (time.time() - t0) * 1000
            nav = get_nav_metrics() or {}
            
            # Wait for three hero canvas if present
            three_canvas = page.query_selector("#three-hero-container canvas")
            
            results["journeys"]["1_initial_landing"] = {
                "server_response_time_ms": nav.get("server_response_time", 0),
                "ttfb_ms": nav.get("ttfb", 0),
                "request_count": len(requests_log),
                "js_execution_rendering_ms": nav.get("js_execution_rendering", 0),
                "time_until_interactive_ms": nav.get("dom_interactive", round(t_interactive)),
                "total_operation_ms": round(total_time),
                "has_three_canvas": bool(three_canvas)
            }
            print(f"  -> TTFB: {nav.get('ttfb')}ms | Interactive: {nav.get('dom_interactive')}ms | Requests: {len(requests_log)} | Total: {round(total_time)}ms")

            # -------------------------------------------------------------
            # Journey 2: Login and authenticated dashboard load
            # -------------------------------------------------------------
            print("\n[Journey 2/9] Measuring Login & Authenticated Dashboard Load...")
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="load")
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')

            requests_log.clear()
            t_click = time.time()
            submit_btn = page.query_selector('button[type="submit"]')
            
            # Measure time until action visibly responds
            page.click('button[type="submit"]')
            t_visible_response = (time.time() - t_click) * 1000
            
            # Wait until dashboard loads
            page.wait_for_selector('main', state='visible')
            t_complete = (time.time() - t_click) * 1000
            nav = get_nav_metrics() or {}

            results["journeys"]["2_login_and_dashboard"] = {
                "server_response_time_ms": nav.get("server_response_time", 0),
                "ttfb_ms": nav.get("ttfb", 0),
                "request_count": len(requests_log),
                "js_execution_rendering_ms": nav.get("js_execution_rendering", 0),
                "time_until_action_visibly_responds_ms": round(t_visible_response, 2),
                "time_until_interactive_ms": nav.get("dom_interactive", 0),
                "total_operation_ms": round(t_complete)
            }
            print(f"  -> Visible Response: {round(t_visible_response)}ms | Dashboard TTFB: {nav.get('ttfb')}ms | Total: {round(t_complete)}ms")

            # -------------------------------------------------------------
            # Journey 3: Navigation between application pages
            # -------------------------------------------------------------
            print("\n[Journey 3/9] Measuring Application Page Navigation...")
            nav_routes = [
                ("Arcs", f"{BASE_URL}/arcs/"),
                ("Tasks", f"{BASE_URL}/tasks/"),
                ("Habits", f"{BASE_URL}/habits/"),
                ("Journal", f"{BASE_URL}/journal/"),
                ("Analytics", f"{BASE_URL}/analytics/")
            ]
            nav_details = {}
            for name, url in nav_routes:
                requests_log.clear()
                t0 = time.time()
                page.goto(url, wait_until="load")
                t_dur = (time.time() - t0) * 1000
                m = get_nav_metrics() or {}
                nav_details[name] = {
                    "ttfb_ms": m.get("ttfb", 0),
                    "dom_interactive_ms": m.get("dom_interactive", 0),
                    "js_rendering_ms": m.get("js_execution_rendering", 0),
                    "request_count": len(requests_log),
                    "total_ms": round(t_dur)
                }
                print(f"  -> {name}: TTFB {m.get('ttfb')}ms | Interactive {m.get('dom_interactive')}ms | Total {round(t_dur)}ms")

            results["journeys"]["3_page_navigation"] = nav_details

            # -------------------------------------------------------------
            # Journey 4: Completing a task or habit
            # -------------------------------------------------------------
            print("\n[Journey 4/9] Measuring In-Place Task & Habit Completion...")
            # On tasks page
            page.goto(f"{BASE_URL}/tasks/", wait_until="load")
            task_btn = page.query_selector('.wa-checkbox-btn')
            task_metrics = {}
            if task_btn:
                requests_log.clear()
                t0 = time.time()
                task_btn.click()
                # Check optimistic feedback
                t_optimistic = time.time()
                t_vis = (t_optimistic - t0) * 1000
                # Wait for fetch completion (loading attribute clears)
                page.wait_for_function('() => !document.querySelector(".wa-checkbox-btn[data-loading=\\"true\\"]")', timeout=10000)
                t_done = (time.time() - t0) * 1000
                task_metrics = {
                    "time_until_visibly_responds_ms": round(t_vis, 2),
                    "total_operation_confirmed_ms": round(t_done),
                    "requests": len(requests_log)
                }
                print(f"  -> Task Toggle: Optimistic {round(t_vis, 2)}ms | Server Confirmed: {round(t_done)}ms")

            # Habit on habits page
            page.goto(f"{BASE_URL}/habits/", wait_until="load")
            habit_btn = page.query_selector('.wa-habit-btn')
            habit_metrics = {}
            if habit_btn:
                requests_log.clear()
                t0 = time.time()
                habit_btn.click()
                t_vis = (time.time() - t0) * 1000
                page.wait_for_function('() => !document.querySelector(".wa-habit-btn[data-loading=\\"true\\"]")', timeout=10000)
                t_done = (time.time() - t0) * 1000
                habit_metrics = {
                    "time_until_visibly_responds_ms": round(t_vis, 2),
                    "total_operation_confirmed_ms": round(t_done),
                    "requests": len(requests_log)
                }
                print(f"  -> Habit Toggle: Optimistic {round(t_vis, 2)}ms | Server Confirmed: {round(t_done)}ms")

            results["journeys"]["4_task_and_habit_completion"] = {
                "task": task_metrics,
                "habit": habit_metrics
            }

            # -------------------------------------------------------------
            # Journey 5: Opening and saving a form
            # -------------------------------------------------------------
            print("\n[Journey 5/9] Measuring Form Open & Save (Create Task)...")
            t0 = time.time()
            page.goto(f"{BASE_URL}/tasks/new/", wait_until="load")
            t_open = (time.time() - t0) * 1000
            nav = get_nav_metrics() or {}
            page.fill('input[name="title"]', f"Speed Audit Task {int(time.time())}")
            
            t_save_start = time.time()
            requests_log.clear()
            page.click('.wa-form-card button[type="submit"]')
            page.wait_for_selector('main', state='visible')
            t_save = (time.time() - t_save_start) * 1000
            nav_save = get_nav_metrics() or {}

            results["journeys"]["5_open_and_save_form"] = {
                "open_form_ttfb_ms": nav.get("ttfb", 0),
                "open_form_total_ms": round(t_open),
                "save_form_ttfb_ms": nav_save.get("ttfb", 0),
                "save_form_total_ms": round(t_save),
                "requests": len(requests_log)
            }
            print(f"  -> Open Form: {round(t_open)}ms | Save & Redirect: {round(t_save)}ms")

            # -------------------------------------------------------------
            # Journey 6: Entering Focus Mode
            # -------------------------------------------------------------
            print("\n[Journey 6/9] Measuring Entering Focus Mode...")
            # Start from dashboard
            page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="load")
            requests_log.clear()
            
            t0 = time.time()
            # On mobile, open menu first if mobile-menu-btn is visible
            mobile_btn = page.query_selector('#mobile-menu-btn')
            if mobile_btn and mobile_btn.is_visible():
                mobile_btn.click()
                page.wait_for_selector('#mobile-menu a[href*="/focus/"]', state='visible', timeout=3000)
                page.click('#mobile-menu a[href*="/focus/"]')
            else:
                focus_link = page.query_selector('a[href*="/focus/"]')
                if focus_link:
                    focus_link.click()
                else:
                    page.goto(f"{BASE_URL}/focus/")
            
            # Wait until focus timer elements are present and interactive
            page.wait_for_selector('#go', state='visible')
            t_interactive = (time.time() - t0) * 1000
            
            # Check font and static asset requests during Focus Mode entry
            focus_fonts = [r["url"] for r in requests_log if "font" in r["url"].lower() or "google" in r["url"].lower()]
            nav = get_nav_metrics() or {}

            results["journeys"]["6_enter_focus_mode"] = {
                "ttfb_ms": nav.get("ttfb", 0),
                "server_response_time_ms": nav.get("server_response_time", 0),
                "request_count": len(requests_log),
                "font_requests_count": len(focus_fonts),
                "font_urls": focus_fonts,
                "time_until_timer_usable_ms": round(t_interactive),
                "total_operation_ms": round(t_interactive)
            }
            print(f"  -> TTFB: {nav.get('ttfb')}ms | Time until Timer Usable: {round(t_interactive)}ms | Requests: {len(requests_log)} (Fonts: {len(focus_fonts)})")

            # -------------------------------------------------------------
            # Journey 7: Exiting Focus Mode and returning to previous state
            # -------------------------------------------------------------
            print("\n[Journey 7/9] Measuring Exiting Focus Mode...")
            t0 = time.time()
            requests_log.clear()
            exit_btn = page.query_selector('.back-to-dashboard')
            if exit_btn:
                exit_btn.click()
            else:
                page.goto(f"{BASE_URL}/accounts/dashboard/")
            
            page.wait_for_selector('main', state='visible')
            t_exit = (time.time() - t0) * 1000
            nav = get_nav_metrics() or {}

            results["journeys"]["7_exit_focus_mode"] = {
                "ttfb_ms": nav.get("ttfb", 0),
                "server_response_time_ms": nav.get("server_response_time", 0),
                "request_count": len(requests_log),
                "time_until_interactive_ms": nav.get("dom_interactive", 0),
                "total_exit_operation_ms": round(t_exit)
            }
            print(f"  -> Exit TTFB: {nav.get('ttfb')}ms | Total Exit Time: {round(t_exit)}ms")

            # -------------------------------------------------------------
            # Journey 8: Repeating Focus Mode entry and exit several times
            # -------------------------------------------------------------
            print("\n[Journey 8/9] Repeating Focus Mode Entry/Exit Cycles (x3)...")
            cycles = []
            for cycle_i in range(1, 4):
                # Enter
                t_in_0 = time.time()
                page.goto(f"{BASE_URL}/focus/", wait_until="load")
                page.wait_for_selector('#go', state='visible')
                t_in = (time.time() - t_in_0) * 1000
                
                # Exit
                t_out_0 = time.time()
                page.click('.back-to-dashboard')
                page.wait_for_selector('main', state='visible')
                t_out = (time.time() - t_out_0) * 1000
                
                cycles.append({
                    "cycle": cycle_i,
                    "enter_ms": round(t_in),
                    "exit_ms": round(t_out),
                    "total_cycle_ms": round(t_in + t_out)
                })
                print(f"  -> Cycle {cycle_i}: Enter {round(t_in)}ms | Exit {round(t_out)}ms | Total {round(t_in + t_out)}ms")

            results["journeys"]["8_repeat_focus_mode_cycles"] = cycles

            # -------------------------------------------------------------
            # Journey 9: Refreshing page after action to confirm persisted state
            # -------------------------------------------------------------
            print("\n[Journey 9/9] Measuring Refresh After Action & State Persistence...")
            page.goto(f"{BASE_URL}/tasks/", wait_until="load")
            requests_log.clear()
            t0 = time.time()
            page.reload(wait_until="load")
            t_reload = (time.time() - t0) * 1000
            nav = get_nav_metrics() or {}

            results["journeys"]["9_refresh_confirm_state"] = {
                "ttfb_ms": nav.get("ttfb", 0),
                "dom_interactive_ms": nav.get("dom_interactive", 0),
                "request_count": len(requests_log),
                "total_reload_ms": round(t_reload)
            }
            print(f"  -> Reload TTFB: {nav.get('ttfb')}ms | Interactive: {nav.get('dom_interactive')}ms | Total: {round(t_reload)}ms")

            browser.close()

    finally:
        if server_process:
            server_process.kill()

    # Save to file
    out_path = "mobile_optimized_audit_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n[DONE] Optimized metrics written to {out_path}")
    return results

if __name__ == '__main__':
    run_baseline_audit()
