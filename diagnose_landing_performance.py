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

def diagnose():
    print("=" * 70)
    print("WINTER ARC LANDING PAGE PERFORMANCE & LCP BOTTLENECK AUDIT")
    print("=" * 70)

    server_process = None
    if not wait_for_server(f"{BASE_URL}/", timeout=2):
        print("Starting Django server on 127.0.0.1:8000...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if not wait_for_server(f"{BASE_URL}/", timeout=30):
            if server_process:
                server_process.kill()
            raise RuntimeError("Could not connect to Django server")
        print("Server running!")

    results = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            viewports = [
                ("Mobile_Throttled", 390, 844, "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148", True, True),
                ("Mobile_Unthrottled", 390, 844, "Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148", True, False),
                ("Desktop_Unthrottled", 1440, 900, "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0", False, False),
            ]

            for label, width, height, ua, is_mobile, throttle in viewports:
                print(f"\n--- Testing: {label} ({width}x{height}) ---")
                context = browser.new_context(viewport={'width': width, 'height': height}, user_agent=ua, is_mobile=is_mobile)
                page = context.new_page()

                # Enable CDP session if throttling
                client = context.new_cdp_session(page)
                if throttle:
                    # Emulate standard Lighthouse Mobile Network (1.6 Mbps download, 750 Kbps upload, 150ms RTT latency)
                    # and CPU throttling (4x)
                    client.send("Network.emulateNetworkConditions", {
                        "offline": False,
                        "latency": 150,
                        "downloadThroughput": (1638400 // 8), # ~204 KB/s
                        "uploadThroughput": (750000 // 8),    # ~93 KB/s
                        "connectionType": "cellular4g"
                    })
                    client.send("Emulation.setCPUThrottlingRate", {"rate": 4})

                network_resources = []
                def on_response(res):
                    try:
                        network_resources.append({
                            "url": res.url,
                            "status": res.status,
                            "type": res.request.resource_type,
                            "size": len(res.body()) if res.status == 200 else 0,
                            "timing": res.request.timing
                        })
                    except Exception:
                        pass
                page.on("response", on_response)

                # Script to record PerformanceObserver LCP before navigation
                page.add_init_script("""
                    window.__lcpEntries = [];
                    window.__paintEntries = [];
                    new PerformanceObserver((entryList) => {
                        for (const entry of entryList.getEntries()) {
                            window.__paintEntries.push({
                                name: entry.name,
                                startTime: entry.startTime
                            });
                        }
                    }).observe({type: 'paint', buffered: true});

                    new PerformanceObserver((entryList) => {
                        for (const entry of entryList.getEntries()) {
                            window.__lcpEntries.push({
                                startTime: entry.startTime,
                                renderTime: entry.renderTime,
                                loadTime: entry.loadTime,
                                size: entry.size,
                                id: entry.id,
                                url: entry.url,
                                elementTag: entry.element ? entry.element.tagName : null,
                                elementId: entry.element ? entry.element.id : null,
                                elementClass: entry.element ? entry.element.className : null,
                                elementHtml: entry.element ? entry.element.outerHTML.substring(0, 300) : null
                            });
                        }
                    }).observe({type: 'largest-contentful-paint', buffered: true});
                """)

                t0 = time.perf_counter()
                page.goto(f"{BASE_URL}/", wait_until="load")
                t_load = time.perf_counter()

                # Wait for loader to disappear if present
                page.wait_for_timeout(3500)
                t_final = time.perf_counter()

                # Evaluate performance metrics
                report = page.evaluate("""() => {
                    const nav = performance.getEntriesByType('navigation')[0];
                    const lcpList = window.__lcpEntries || [];
                    const paintList = window.__paintEntries || [];
                    const fcp = paintList.find(p => p.name === 'first-contentful-paint');

                    // Check elements in viewport
                    const hero = document.getElementById('hero');
                    const heroHeading = hero ? hero.querySelector('h1') : null;
                    const heroImg = hero ? hero.querySelector('.bg-cover') : null;

                    return {
                        navTimings: {
                            ttfb: nav ? nav.responseStart - nav.requestStart : 0,
                            domContentLoaded: nav ? nav.domContentLoadedEventEnd : 0,
                            loadEvent: nav ? nav.loadEventEnd : 0
                        },
                        fcp: fcp ? fcp.startTime : 0,
                        lcpEntries: lcpList,
                        lastLCP: lcpList.length > 0 ? lcpList[lcpList.length - 1] : null
                    };
                }""")

                # Collect total payload
                total_bytes = sum(r["size"] for r in network_resources)
                image_bytes = sum(r["size"] for r in network_resources if r["type"] == "image")
                js_bytes = sum(r["size"] for r in network_resources if r["type"] == "script")
                css_bytes = sum(r["size"] for r in network_resources if r["type"] == "stylesheet")
                font_bytes = sum(r["size"] for r in network_resources if r["type"] == "font")

                # Sort largest resources
                largest_resources = sorted(network_resources, key=lambda x: x["size"], reverse=True)[:10]

                print(f"  Total Transferred: {total_bytes / 1024:.1f} KiB")
                print(f"    - Images: {image_bytes / 1024:.1f} KiB ({len([r for r in network_resources if r['type'] == 'image'])} images)")
                print(f"    - JS: {js_bytes / 1024:.1f} KiB")
                print(f"    - CSS: {css_bytes / 1024:.1f} KiB")
                print(f"    - Fonts: {font_bytes / 1024:.1f} KiB")
                print(f"  FCP: {report['fcp']:.1f} ms | DCL: {report['navTimings']['domContentLoaded']:.1f} ms | Load: {report['navTimings']['loadEvent']:.1f} ms")

                lcp = report["lastLCP"]
                if lcp:
                    print(f"  LCP Element: <{lcp['elementTag']} id='{lcp['elementId']}' class='{lcp['elementClass']}'>")
                    print(f"    LCP Time: {lcp['startTime']:.1f} ms (LoadTime: {lcp['loadTime']:.1f} ms, RenderTime: {lcp['renderTime']:.1f} ms)")
                    print(f"    LCP Resource URL: {lcp['url']}")
                    print(f"    LCP Snippet: {lcp['elementHtml'][:120]}...")
                else:
                    print("  No LCP entry detected.")

                print("\n  Top 5 Largest Network Resources:")
                for r in largest_resources[:5]:
                    url_short = r["url"].split("/")[-1] or r["url"]
                    print(f"    - [{r['type'].upper()}] {url_short}: {r['size'] / 1024:.1f} KiB")

                results[label] = {
                    "total_bytes": total_bytes,
                    "image_bytes": image_bytes,
                    "js_bytes": js_bytes,
                    "css_bytes": css_bytes,
                    "font_bytes": font_bytes,
                    "fcp": report["fcp"],
                    "navTimings": report["navTimings"],
                    "lcp": lcp,
                    "allLcpEntries": report["lcpEntries"],
                    "largest_resources": largest_resources
                }

                context.close()

            browser.close()

    finally:
        if server_process:
            server_process.kill()

    with open("landing_diagnostics.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\nDiagnostic complete! Written to landing_diagnostics.json")

if __name__ == "__main__":
    diagnose()
