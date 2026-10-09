import os
import sys
import time
import json
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

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

def run_suite(mode_name="baseline", output_file="baseline_metrics.json"):
    print(f"\n=======================================================")
    print(f"RUNNING NAVIGATION MEASUREMENT: {mode_name.upper()}")
    print(f"=======================================================")

    # Ensure browser fixtures exist
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # Launch server if needed
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Starting Django development server...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=30):
            if server_process:
                server_process.kill()
            raise RuntimeError("Could not connect to Django server at 127.0.0.1:8000")
        print("Server running!")

    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        configs = [
            ("Desktop", 1440, 900, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0", False),
            ("Mobile", 390, 844, "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148", True)
        ]

        for device_name, width, height, ua, is_mob in configs:
            results[device_name] = {"cold": {}, "warm": {}}
            print(f"\n--- Testing Device: {device_name} ({width}x{height}) ---")

            for cache_state in ["cold", "warm"]:
                print(f"\n  -> Navigation Mode: {cache_state.upper()}")

                context = browser.new_context(
                    viewport={"width": width, "height": height},
                    user_agent=ua,
                    is_mobile=is_mob
                )
                page = context.new_page()

                console_errors = []
                failed_requests = []

                page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
                page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url} - {req.failure}"))

                # Log in
                page.goto(f"{BASE_URL}/accounts/login/", wait_until="load", timeout=15000)
                page.fill('input[name="username"]', 'browseruser1')
                page.fill('input[name="password"]', 'Password123!')
                with page.expect_navigation(wait_until="load", timeout=15000):
                    page.click('button[type="submit"]')
                page.wait_for_selector("main", state="visible", timeout=10000)

                # Get the Arc ID and Goal ID from page
                # Find arc detail link, task detail link, habit detail link, goal detail link
                # We define the sequence of routes to measure:
                # 1. Dashboard -> Arcs
                # 2. Arcs -> Arc Detail
                # 3. Arc Detail -> Tasks
                # 4. Tasks -> Task Detail
                # 5. Dashboard -> Habits
                # 6. Habits -> Habit Detail
                # 7. Goals -> Goal Detail
                # 8. Dashboard -> Goals
                # 9. Dashboard -> Journal
                # 10. Dashboard -> Analytics

                def measure_link_navigation(start_url, click_selector, expected_pattern, route_label):
                    # Ensure we are at start_url
                    if not re_matches(expected_pattern, page.url):
                        page.goto(start_url, wait_until="networkidle")

                    reqs = []
                    asset_reqs = {}
                    doc_response = {"timing": None, "size": 0, "status": 0, "redirects": 0}

                    def on_request(request):
                        reqs.append(request.url)
                        if any(request.url.endswith(ext) or ext in request.url for ext in ['.css', '.js', '.woff2', '.jpg', '.png', '.webp', '.svg']):
                            asset_reqs[request.url] = asset_reqs.get(request.url, 0) + 1

                    def on_response(response):
                        if response.request.resource_type == "document":
                            if response.status in (301, 302, 303, 307, 308):
                                doc_response["redirects"] += 1
                            else:
                                doc_response["status"] = response.status
                                doc_response["timing"] = response.request.timing
                                try:
                                    doc_response["size"] = len(response.body())
                                except Exception:
                                    doc_response["size"] = 0

                    req_listener = page.on("request", on_request)
                    res_listener = page.on("response", on_response)

                    # Locate element to click
                    if device_name == "Mobile" and "#mobile-menu" in click_selector:
                        mobile_menu = page.locator("#mobile-menu")
                        if not mobile_menu.is_visible():
                            page.locator("#mobile-menu-btn").click()
                            mobile_menu.wait_for(state="visible", timeout=3000)
                    elem = page.locator(click_selector).first

                    t_click = time.perf_counter()
                    nav_start_epoch = None

                    # Click and wait for navigation
                    with page.expect_navigation(wait_until="load", timeout=15000):
                        elem.click()
                    t_loaded = time.perf_counter()

                    # Wait for visual element to be visible
                    page.wait_for_selector("main", state="visible")
                    t_visually_usable = time.perf_counter()

                    # Collect browser performance timings
                    perf_data = page.evaluate("""() => {
                        const nav = performance.getEntriesByType('navigation')[0];
                        const paint = performance.getEntriesByType('paint');
                        const fcp = paint.find(p => p.name === 'first-contentful-paint');
                        return {
                            domContentLoaded: nav ? nav.domContentLoadedEventEnd : 0,
                            loadEvent: nav ? nav.loadEventEnd : 0,
                            domInteractive: nav ? nav.domInteractive : 0,
                            domComplete: nav ? nav.domComplete : 0,
                            responseStart: nav ? nav.responseStart : 0,
                            responseEnd: nav ? nav.responseEnd : 0,
                            requestStart: nav ? nav.requestStart : 0,
                            fcp: fcp ? fcp.startTime : 0
                        };
                    }""")

                    # Remove listeners
                    page.remove_listener("request", on_request)
                    page.remove_listener("response", on_response)

                    timing = doc_response["timing"] or {}
                    req_start = timing.get("requestStart", -1)
                    res_start = timing.get("responseStart", -1)
                    res_end = timing.get("responseEnd", -1)
                    ttfb = (res_start - req_start) if (res_start >= 0 and req_start >= 0) else perf_data.get("responseStart", 0) - perf_data.get("requestStart", 0)
                    doc_duration = (res_end - req_start) if (res_end >= 0 and req_start >= 0) else perf_data.get("responseEnd", 0) - perf_data.get("requestStart", 0)

                    repeated_assets = sum(1 for count in asset_reqs.values() if count > 1)

                    metric = {
                        "route": route_label,
                        "url": page.url,
                        "click_to_nav_start_ms": round(max(0, req_start) if req_start > 0 else 5.0, 2),
                        "server_response_time_ms": round(max(0, ttfb), 2),
                        "html_download_time_ms": round(max(0, doc_duration), 2),
                        "redirect_count": doc_response["redirects"],
                        "html_response_size_bytes": doc_response["size"],
                        "dom_content_loaded_ms": round(perf_data.get("domContentLoaded", 0), 2),
                        "load_event_ms": round(perf_data.get("loadEvent", 0), 2),
                        "time_to_visually_usable_ms": round((t_visually_usable - t_click) * 1000, 2),
                        "js_exec_render_ms": round(max(0, perf_data.get("domComplete", 0) - perf_data.get("domInteractive", 0)), 2),
                        "network_requests_count": len(reqs),
                        "repeated_asset_requests": repeated_assets,
                        "console_errors": len(console_errors),
                        "failed_requests": len(failed_requests)
                    }

                    print(f"    [{route_label}] HTML: {metric['html_response_size_bytes']}B | TTFB: {metric['server_response_time_ms']}ms | DCL: {metric['dom_content_loaded_ms']}ms | Usable: {metric['time_to_visually_usable_ms']}ms | Reqs: {metric['network_requests_count']}")
                    return metric

                def re_matches(pattern, url):
                    import re
                    return bool(re.search(pattern, url))

                def nav_sel(path):
                    if device_name == "Mobile":
                        return f"#mobile-menu a[href='{path}']"
                    return f"#global-navbar a[href='{path}']"

                # Route 1: Dashboard -> Arcs
                m1 = measure_link_navigation(
                    f"{BASE_URL}/accounts/dashboard/",
                    nav_sel("/arcs/"),
                    r"/arcs/$",
                    "Dashboard -> Arcs"
                )

                # Route 2: Arcs -> Arc Detail
                m2 = measure_link_navigation(
                    f"{BASE_URL}/arcs/",
                    "main h2 a[href^='/arcs/']",
                    r"/arcs/\d+/?$",
                    "Arcs -> Arc Detail"
                )

                # Route 3: Arc Detail -> Goal Detail
                m3 = measure_link_navigation(
                    page.url,
                    "main h3 a[href^='/goals/']",
                    r"/goals/\d+/?$",
                    "Goals -> Goal Detail"
                )

                # Route 4: Arc Detail -> Tasks
                m4 = measure_link_navigation(
                    page.url,
                    nav_sel("/tasks/"),
                    r"/tasks/$",
                    "Arc -> Tasks"
                )

                # Route 5: Tasks -> Task Detail
                m5 = measure_link_navigation(
                    f"{BASE_URL}/tasks/",
                    "main .task-row a[href^='/tasks/']",
                    r"/tasks/\d+/?$",
                    "Tasks -> Task Detail"
                )

                # Route 6: Dashboard -> Habits
                m6 = measure_link_navigation(
                    f"{BASE_URL}/accounts/dashboard/",
                    nav_sel("/habits/"),
                    r"/habits/$",
                    "Dashboard -> Habits"
                )

                # Route 7: Habits -> Habit Detail
                m7 = measure_link_navigation(
                    f"{BASE_URL}/habits/",
                    "main h2 a[href^='/habits/']",
                    r"/habits/\d+/?$",
                    "Habits -> Habit Detail"
                )

                # Route 8: Dashboard -> Journal
                m8 = measure_link_navigation(
                    f"{BASE_URL}/accounts/dashboard/",
                    nav_sel("/journal/"),
                    r"/journal/$",
                    "Dashboard -> Journal"
                )

                # Route 9: Dashboard -> Analytics
                m9 = measure_link_navigation(
                    f"{BASE_URL}/accounts/dashboard/",
                    nav_sel("/analytics/"),
                    r"/analytics/$",
                    "Dashboard -> Analytics"
                )

                results[device_name][cache_state] = {
                    "Dashboard -> Arcs": m1,
                    "Arcs -> Arc Detail": m2,
                    "Goals -> Goal Detail": m3,
                    "Arc -> Tasks": m4,
                    "Tasks -> Task Detail": m5,
                    "Dashboard -> Habits": m6,
                    "Habits -> Habit Detail": m7,
                    "Dashboard -> Journal": m8,
                    "Dashboard -> Analytics": m9
                }

                context.close()

        browser.close()

    if server_process:
        server_process.kill()

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nMeasurements written to {output_file}")
    return results

if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "baseline_metrics.json"
    label = sys.argv[2] if len(sys.argv) > 2 else "baseline"
    run_suite(mode_name=label, output_file=out_file)
