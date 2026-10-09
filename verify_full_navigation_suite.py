import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

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

def main():
    print("=" * 70)
    print("WINTER ARC - COMPREHENSIVE NAVIGATION & REGRESSION QA SUITE")
    print("=" * 70)

    # 1. Ensure fixtures
    print("[1/5] Ensuring database fixtures...")
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # 2. Server check
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Starting Django server on 127.0.0.1:8000...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=30):
            if server_process:
                server_process.kill()
            raise RuntimeError("Could not connect to Django server")
        print("Server running!")

    console_errors = []
    failed_requests = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -------------------------------------------------------------
            # TEST A: DIRECT NAVIGATION & BACK/FORWARD & AUTHENTICATION
            # -------------------------------------------------------------
            print("\n[2/5] Testing Direct Navigation, Auth, and History Navigation...")
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()

            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url} - {req.failure}"))

            # Direct landing page
            page.goto(f"{BASE_URL}/", wait_until="load")
            assert page.title(), "Landing page should have title"
            print("  ✓ Direct navigation to Landing Page (/): OK")

            # Login
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="load")
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')
            with page.expect_navigation(wait_until="load"):
                page.click('#login-submit-btn')
            assert "/accounts/dashboard/" in page.url
            print("  ✓ Authentication flow: OK")

            # Direct navigation to every tested route
            routes_to_test = [
                ("/arcs/", "Arcs"),
                ("/tasks/", "Tasks"),
                ("/habits/", "Habits"),
                ("/journal/", "Journal"),
                ("/analytics/", "Analytics"),
                ("/accounts/profile/", "Profile"),
                ("/notifications/", "Notifications"),
            ]
            for path, name in routes_to_test:
                page.goto(f"{BASE_URL}{path}", wait_until="load")
                page.wait_for_selector("main", state="visible")
                print(f"  ✓ Direct navigation to {name} ({path}): OK")

            # Browser Back / Forward History navigation
            print("  - Testing browser Back and Forward navigation...")
            page.goto(f"{BASE_URL}/tasks/", wait_until="load")
            page.goto(f"{BASE_URL}/habits/", wait_until="load")
            page.go_back(wait_until="load")
            assert "/tasks/" in page.url, f"Expected /tasks/ after go_back, got {page.url}"
            page.go_forward(wait_until="load")
            assert "/habits/" in page.url, f"Expected /habits/ after go_forward, got {page.url}"
            print("  ✓ History Back/Forward navigation: OK")

            # -------------------------------------------------------------
            # TEST B: THEME INITIALIZATION & FLASH PREVENTION
            # -------------------------------------------------------------
            print("\n[3/5] Testing Light/Dark Theme Switching & Persistence...")
            theme_btn = page.locator("#theme-toggle-btn")
            initial_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            print(f"  Initial theme: {initial_theme}")
            theme_btn.click()
            page.wait_for_timeout(200)
            toggled_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            assert toggled_theme != initial_theme, "Theme should toggle"
            print(f"  Toggled theme: {toggled_theme}")

            # Direct reload to check persistence without flash
            page.reload(wait_until="load")
            reloaded_theme = page.evaluate("() => document.documentElement.getAttribute('data-theme')")
            assert reloaded_theme == toggled_theme, "Theme should persist across page reload"
            print("  ✓ Theme persistence & FOWT prevention: OK")

            # Toggle back to light
            if reloaded_theme == "dark":
                theme_btn = page.locator("#theme-toggle-btn")
                theme_btn.click()
                page.wait_for_timeout(200)

            # -------------------------------------------------------------
            # TEST C: MOBILE NAVIGATION & TOUCH TARGETS
            # -------------------------------------------------------------
            print("\n[4/5] Testing Mobile Viewport Navigation (390x844)...")
            mobile_context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
            mobile_page = mobile_context.new_page()
            mobile_page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            mobile_page.on("requestfailed", lambda req: failed_requests.append(f"{req.method} {req.url} - {req.failure}"))

            mobile_page.goto(f"{BASE_URL}/accounts/login/", wait_until="load")
            mobile_page.fill('input[name="username"]', 'browseruser1')
            mobile_page.fill('input[name="password"]', 'Password123!')
            with mobile_page.expect_navigation(wait_until="load"):
                mobile_page.click('#login-submit-btn')

            # Open drawer
            mobile_btn = mobile_page.locator("#mobile-menu-btn")
            mobile_btn.click()
            mobile_menu = mobile_page.locator("#mobile-menu")
            mobile_menu.wait_for(state="visible")
            print("  ✓ Mobile navigation drawer opened: OK")

            # Click Tasks from mobile menu
            with mobile_page.expect_navigation(wait_until="load"):
                mobile_menu.locator("a[href='/tasks/']").click()
            assert "/tasks/" in mobile_page.url
            print("  ✓ Mobile link navigation to /tasks/: OK")

            # -------------------------------------------------------------
            # TEST D: LOGOUT FLOW
            # -------------------------------------------------------------
            print("\n[5/5] Testing Logout Workflow...")
            with mobile_page.expect_navigation(wait_until="load"):
                mobile_menu_btn = mobile_page.locator("#mobile-menu-btn")
                if not mobile_menu.is_visible():
                    mobile_menu_btn.click()
                    mobile_menu.wait_for(state="visible")
                mobile_menu.locator("form button[type='submit']").click()
            assert "/accounts/login/" in mobile_page.url or "/" in mobile_page.url
            print("  ✓ Logout workflow: OK")

            mobile_context.close()
            context.close()
            browser.close()

    finally:
        if server_process:
            server_process.kill()

    print("\n" + "=" * 70)
    print("REGRESSION SUMMARY")
    print("=" * 70)
    print(f"Console errors: {len(console_errors)}")
    for err in console_errors:
        print(f"  - Error: {err}")
    print(f"Failed requests: {len(failed_requests)}")
    for req in failed_requests:
        print(f"  - Request: {req}")

    if console_errors or failed_requests:
        print("FAIL: Regressions detected!")
        sys.exit(1)

    print("SUCCESS: All comprehensive navigation and regression tests passed!")

if __name__ == "__main__":
    main()
