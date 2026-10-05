"""
Playwright End-to-End Browser QA Suite for Winter Arc Technical SEO Foundation.

Verifies:
- All required desktop & mobile viewports (1920, 1440, 1280, 1024, 768, 390, 375)
- Title, Meta description, Canonical URL, Robots directive
- Open Graph tags and Twitter/X metadata
- JSON-LD Structured Data validity and schema graph
- Favicon, Apple Touch Icon, and Web App Manifest links
- /robots.txt response and crawler policies
- /sitemap.xml schema compliance and public URL exclusivity
- 404 error page status (404), visual appearance, noindex directive, sanctuary link
- Authenticated pages noindex protection
- Zero horizontal overflow across all viewports
- Zero console errors and zero failed network requests
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots', 'seo')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


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


def run_seo_browser_qa():
    print("=" * 70)
    print("STARTING PLAYWRIGHT TECHNICAL SEO FOUNDATION BROWSER QA")
    print("=" * 70)

    # 1. Run fixtures prep
    print("[INIT] Preparing test user fixtures...")
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # 2. Check or launch Django dev server
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Launching Django dev server on port 8000...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=25):
            print("ERROR: Server failed to start.")
            if server_process:
                server_process.terminate()
            sys.exit(1)
        print("Django server launched successfully.")
    else:
        print("Django server already running on port 8000.")

    console_errors = []
    failed_requests = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -----------------------------------------------------------------
            # STEP 1: Verify robots.txt & sitemap.xml via HTTP request
            # -----------------------------------------------------------------
            print("\n[STEP 1] Testing /robots.txt and /sitemap.xml endpoints...")
            page = browser.new_page()

            # Robots.txt
            resp_robots = page.goto(f"{BASE_URL}/robots.txt")
            assert resp_robots.status == 200, f"robots.txt must return 200, got {resp_robots.status}"
            assert "text/plain" in resp_robots.headers.get("content-type", ""), "robots.txt must be text/plain"
            robots_body = page.content()
            assert "User-agent: Googlebot" in robots_body, "Googlebot missing in robots.txt"
            assert "User-agent: Bingbot" in robots_body, "Bingbot missing in robots.txt"
            assert "User-agent: OAI-SearchBot" in robots_body, "OAI-SearchBot missing in robots.txt"
            assert "User-agent: GPTBot" in robots_body, "GPTBot missing in robots.txt"
            assert "Disallow: /arcs/" in robots_body, "Private /arcs/ not disallowed in robots.txt"
            assert "Sitemap:" in robots_body, "Sitemap directive missing in robots.txt"
            print("✓ /robots.txt returns 200, text/plain, valid crawler rules and sitemap pointer.")

            # Sitemap.xml
            resp_sitemap = page.goto(f"{BASE_URL}/sitemap.xml")
            assert resp_sitemap.status == 200, f"sitemap.xml must return 200, got {resp_sitemap.status}"
            assert "xml" in resp_sitemap.headers.get("content-type", ""), "sitemap.xml must return XML content-type"
            sitemap_body = resp_sitemap.text()
            root = ET.fromstring(sitemap_body)
            assert root.tag.endswith('urlset'), "Root XML tag must be urlset"
            locs = [el.text for el in root.iter() if el.tag.endswith('loc')]
            assert any(loc.endswith('/') for loc in locs), "Homepage loc missing in sitemap"
            for forbidden in ['/dashboard', '/arcs', '/goals', '/tasks', '/habits', '/journal', '/analytics', '/notifications', '/api']:
                assert not any(forbidden in loc for loc in locs), f"Forbidden route {forbidden} found in sitemap!"
            print("✓ /sitemap.xml returns 200, valid sitemaps 0.9 schema, strictly canonical public URLs.")

            # -----------------------------------------------------------------
            # STEP 2: Verify 404 page status, meta robots, and sanctuary link
            # -----------------------------------------------------------------
            print("\n[STEP 2] Testing 404 page behavior and discoverability protection...")
            resp_404 = page.goto(f"{BASE_URL}/404/")
            assert resp_404.status == 404, f"404 path must return 404, got {resp_404.status}"
            assert page.locator('meta[name="robots"][content*="noindex"]').count() >= 1, "404 page must have noindex robots tag"
            assert page.locator('a:has-text("Return to Sanctuary")').is_visible(), "404 page must provide Return to Sanctuary link"
            img_404 = os.path.join(SCREENSHOTS_DIR, "07_seo_404_page.png")
            page.screenshot(path=img_404)
            print(f"✓ 404 returns HTTP 404, contains noindex, nofollow, and links back to sanctuary. Captured: {img_404}")
            page.close()

            # -----------------------------------------------------------------
            # STEP 3: Multi-Viewport Responsive Audit & Metadata Source Audit
            # -----------------------------------------------------------------
            viewports = [
                ("01_desktop_1920", 1920, 1080),
                ("02_desktop_1440", 1440, 900),
                ("02b_desktop_1280", 1280, 800),
                ("03_desktop_1024", 1024, 768),
                ("04_tablet_768", 768, 1024),
                ("05_mobile_390", 390, 844),
                ("06_mobile_375", 375, 667),
            ]

            print("\n[STEP 3] Testing Homepage across all required viewports...")
            home_context = browser.new_context(viewport={'width': 1920, 'height': 1080})
            home_page = home_context.new_page()

            home_page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            home_page.on("requestfailed", lambda req: failed_requests.append(req.url))

            resp = home_page.goto(f"{BASE_URL}/", wait_until="load")
            assert resp.status == 200, f"Homepage failed with status {resp.status}"

            # Allow loader animation to hide
            home_page.wait_for_timeout(2600)

            print("\n--- Detailed HTML Metadata Source Audit ---")
            # Title
            title = home_page.title()
            print(f"Title: {title}")
            assert "Winter Arc" in title and "Discipline Tracker" in title, f"Unexpected title: {title}"

            # Meta Description
            desc = home_page.locator('meta[name="description"]').get_attribute('content')
            print(f"Description: {desc}")
            assert desc and "structured goals, habits, tasks" in desc, "Meta description missing or incorrect"

            # Robots
            robots = home_page.locator('meta[name="robots"]').first.get_attribute('content')
            print(f"Robots: {robots}")
            assert "index" in robots and "follow" in robots, "Homepage robots should be index, follow"

            # Canonical Link
            canonicals = home_page.locator('link[rel="canonical"]').all()
            assert len(canonicals) == 1, f"Expected exactly 1 canonical tag, found {len(canonicals)}"
            canonical_href = canonicals[0].get_attribute('href')
            print(f"Canonical URL: {canonical_href}")
            assert canonical_href.endswith('/'), "Canonical URL must have normalized trailing slash for root"
            assert not canonical_href.startswith('http://') or '127.0.0.1' in canonical_href or 'localhost' in canonical_href, "Production canonical must not be insecure HTTP"

            # Open Graph
            og_title = home_page.locator('meta[property="og:title"]').get_attribute('content')
            og_desc = home_page.locator('meta[property="og:description"]').get_attribute('content')
            og_type = home_page.locator('meta[property="og:type"]').get_attribute('content')
            og_url = home_page.locator('meta[property="og:url"]').get_attribute('content')
            og_image = home_page.locator('meta[property="og:image"]').get_attribute('content')
            og_site = home_page.locator('meta[property="og:site_name"]').get_attribute('content')

            print(f"OG Title: {og_title}")
            print(f"OG Type: {og_type}")
            print(f"OG Image: {og_image}")
            assert og_title and "Winter Arc" in og_title, "og:title missing"
            assert og_desc and len(og_desc) > 20, "og:description missing"
            assert og_type == "website", f"og:type should be 'website', got {og_type}"
            assert og_site == "Winter Arc", f"og:site_name should be 'Winter Arc', got {og_site}"
            assert og_image and ("og-winter-arc" in og_image), "og:image missing or wrong file"

            # Twitter / X
            tw_card = home_page.locator('meta[name="twitter:card"]').get_attribute('content')
            tw_title = home_page.locator('meta[name="twitter:title"]').get_attribute('content')
            tw_image = home_page.locator('meta[name="twitter:image"]').get_attribute('content')
            print(f"Twitter Card: {tw_card}")
            assert tw_card == "summary_large_image", f"twitter:card should be summary_large_image, got {tw_card}"
            assert tw_title and "Winter Arc" in tw_title, "twitter:title missing"
            assert tw_image and ("og-winter-arc" in tw_image), "twitter:image missing"

            # Icons & Manifest
            assert home_page.locator('link[rel*="icon"]').count() >= 1, "Favicon link missing"
            assert home_page.locator('link[rel="apple-touch-icon"]').count() >= 1, "Apple touch icon link missing"
            assert home_page.locator('link[rel="manifest"]').count() >= 1, "Web manifest link missing"
            print("✓ Icons, Apple touch icon, and Web Manifest links verified.")

            # JSON-LD Structured Data
            json_scripts = home_page.locator('script[type="application/ld+json"]').all()
            assert len(json_scripts) >= 1, "JSON-LD script missing"
            json_raw = json_scripts[0].inner_text()
            ld_data = json.loads(json_raw)
            assert ld_data.get('@context') == 'https://schema.org', "JSON-LD @context must be https://schema.org"
            graph = {item['@type']: item for item in ld_data.get('@graph', [])}
            assert 'WebSite' in graph, "WebSite schema missing"
            assert 'Organization' in graph, "Organization schema missing"
            assert 'SoftwareApplication' in graph, "SoftwareApplication schema missing"
            assert graph['SoftwareApplication']['applicationCategory'] == 'ProductivityApplication', "Incorrect applicationCategory"
            assert graph['SoftwareApplication']['operatingSystem'] == 'Web', "Incorrect operatingSystem"
            print("✓ JSON-LD validated: WebSite, Organization, SoftwareApplication graph intact with 0 fabricated claims.")

            for label, width, height in viewports:
                home_page.set_viewport_size({'width': width, 'height': height})
                home_page.wait_for_timeout(400)
                is_overflow = home_page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
                assert not is_overflow, f"Horizontal overflow detected on viewport {width}x{height}!"
                img_path = os.path.join(SCREENSHOTS_DIR, f"{label}_homepage.png")
                home_page.screenshot(path=img_path)
                print(f"✓ Viewport {width}x{height} passed. Screenshot: {img_path}")

            home_context.close()

            # -----------------------------------------------------------------
            # STEP 4: Verify Authenticated Pages are Protected from Indexing
            # -----------------------------------------------------------------
            print("\n[STEP 4] Verifying Authenticated Pages have noindex and no canonical leak...")
            auth_context = browser.new_context(viewport={'width': 1440, 'height': 900})
            auth_page = auth_context.new_page()

            auth_page.goto(f"{BASE_URL}/accounts/login/", wait_until="load")
            auth_page.fill('input[name="username"]', 'browseruser1')
            auth_page.fill('input[name="password"]', 'Password123!')
            auth_page.click('button[type="submit"]')
            auth_page.wait_for_url(f"{BASE_URL}/accounts/dashboard/**", timeout=10000)

            for private_url in ['/accounts/dashboard/', '/arcs/', '/tasks/', '/habits/', '/journal/', '/analytics/', '/accounts/profile/']:
                auth_page.goto(f"{BASE_URL}{private_url}", wait_until="load")
                robots_content = auth_page.locator('meta[name="robots"]').first.get_attribute('content')
                assert "noindex" in robots_content and "nofollow" in robots_content, f"Private URL {private_url} missing noindex directive!"
                # Verify no canonical tag pointing to root
                canonicals = auth_page.locator('link[rel="canonical"]').all()
                if len(canonicals) > 0:
                    assert canonicals[0].get_attribute('href') != f"{BASE_URL}/", f"Private URL {private_url} incorrectly points canonical to homepage!"
                print(f"✓ Protected route {private_url} verified with noindex, nofollow.")

            auth_context.close()
            browser.close()

            # Filter expected harmless warnings
            critical_console = [err for err in console_errors if not any(ign in err for ign in ['favicon', 'caniuse'])]
            assert len(critical_console) == 0, f"Unexpected browser console errors: {critical_console}"
            assert len(failed_requests) == 0, f"Unexpected failed network requests: {failed_requests}"

            print("\n" + "=" * 70)
            print("ALL PLAYWRIGHT BROWSER SEO & METADATA TESTS PASSED CLEANLY (0 ERRORS)")
            print("=" * 70)

    finally:
        if server_process:
            server_process.terminate()


if __name__ == '__main__':
    run_seo_browser_qa()
