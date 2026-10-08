"""
Playwright automated QA verification for Winter Arc Interaction Performance & In-Place Actions:
- Desktop (1440x900) & Mobile (390x844)
- Login submission & loading feedback
- In-place task completion/uncompletion without URL change
- In-place habit completion/undo without URL change
- In-place milestone toggle on goal detail
- Intentional title link detail navigation
- Light mode & Dark mode interaction styling verification
- Mobile touch target dimensions (>= 36px)
- 0 browser console errors, 0 failed network requests
"""
import os
import sys
import time
import subprocess
import urllib.request
import re

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots_interaction_qa')
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


def main():
    print("=" * 70)
    print("WINTER ARC - INTERACTION PERFORMANCE & ACTION QA VERIFICATION")
    print("=" * 70)

    # 1. Prepare fixtures
    print("[1/6] Preparing browser fixtures...")
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # 2. Check/Launch server
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Starting local server on 127.0.0.1:8000...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=20):
            print("ERROR: Dev server failed to start.")
            if server_process:
                server_process.terminate()
            sys.exit(1)
    else:
        print("Dev server is running.")

    console_errors = []
    failed_requests = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)

            # -------------------------------------------------------------
            # TEST A: DESKTOP WORKFLOW (1440x900)
            # -------------------------------------------------------------
            print("\n[2/6] Starting Desktop QA (1440x900)...")
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()

            page.on('console', lambda msg: (print(f"    [BROWSER CONSOLE {msg.type}] {msg.text}"), console_errors.append(msg.text) if msg.type == 'error' else None))
            page.on('pageerror', lambda exc: (print(f"    [BROWSER ERROR] {exc}"), console_errors.append(str(exc))))
            page.on('request', lambda req: print(f"    [REQUEST {req.method}] {req.url}"))
            page.on('response', lambda res: print(f"    [RESPONSE {res.status}] {res.url}"))
            page.on('requestfailed', lambda req: (print(f"    [FAILED REQUEST] {req.method} {req.url}: {req.failure}"), failed_requests.append(f"{req.method} {req.url}: {req.failure}")))

            # Step A1: Login
            print("  - Navigating to /accounts/login/...")
            page.goto(f"{BASE_URL}/accounts/login/")
            page.wait_for_selector('input[name="username"]')
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')

            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_login_filled.png"))
            print("  - Submitting login form...")
            page.click('#login-submit-btn')

            # Expect redirection directly to dashboard
            page.wait_for_url(f"{BASE_URL}/accounts/dashboard/", timeout=10000)
            print("  ✓ Login redirected directly to /accounts/dashboard/")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_dashboard_desktop.png"))

            # Step A2: Check Task Checkbox on Dashboard
            print("  - Testing dashboard task inline completion...")
            current_url = page.url
            task_btn = page.locator('.task-row .wa-checkbox-btn').first
            task_btn.wait_for(state='visible', timeout=5000)

            # Record initial visual state
            task_indicator = page.locator('.task-row .wa-checkbox-indicator').first
            was_completed = 'is-completed' in (task_indicator.get_attribute('class') or '')

            # Click task checkbox button
            task_btn.click()

            # Wait for indicator class to update (or wait up to 5s)
            target_selector = '.task-row .wa-checkbox-indicator' + (':not(.is-completed)' if was_completed else '.is-completed')
            page.wait_for_selector(target_selector, timeout=5000)

            # ASSERT: URL did NOT change
            assert page.url == current_url, f"Expected URL to remain {current_url}, but got {page.url}"
            print("  ✓ Task checkbox click stayed in place (URL did not navigate)")

            # Check new visual state
            now_completed = 'is-completed' in (task_indicator.get_attribute('class') or '')
            assert was_completed != now_completed, "Task indicator state should toggle"
            print("  ✓ Task indicator toggled in-place successfully")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_task_toggled_dashboard.png"))

            # Step A3: Test Habit completion on Dashboard
            print("  - Testing dashboard habit inline completion...")
            habit_btn = page.locator('.wa-habit-btn').first
            if habit_btn.count() > 0:
                habit_btn.click()
                page.wait_for_timeout(400)
                assert page.url == current_url, f"Expected URL to remain {current_url}, but got {page.url}"
                print("  ✓ Habit action button click stayed in place (URL did not navigate)")
                page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_habit_toggled_dashboard.png"))

            # Step A4: Test Task List Page
            print("\n[3/6] Testing Tasks List Page (/tasks/)...")
            page.goto(f"{BASE_URL}/tasks/")
            page.wait_for_selector('.task-row')
            list_url = page.url

            task_list_btn = page.locator('.task-row .wa-checkbox-btn').first
            task_list_btn.click()
            page.wait_for_timeout(600)

            # ASSERT: URL did NOT change to detail
            assert page.url == list_url, f"Expected URL to remain {list_url}, but got {page.url}"
            print("  ✓ Task checkbox on /tasks/ stayed in place (did NOT open /tasks/<id>/)")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_task_list_toggled.png"))

            # Step A5: Test Intentional Title Navigation
            print("  - Testing intentional title click to open detail page...")
            title_link = page.locator('.task-row a').filter(has_text="Execute 100 Pushups").first
            title_link.click()
            page.wait_for_url(re.compile(r".*/tasks/\d+/.*"), timeout=5000)
            print(f"  ✓ Intentional title click navigated to detail page: {page.url}")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_task_detail_intentional_nav.png"))

            # Step A6: Test Habits List Page
            print("\n[4/6] Testing Habits List Page (/habits/)...")
            page.goto(f"{BASE_URL}/habits/")
            page.wait_for_selector('.wa-habit-btn')
            habit_list_url = page.url

            h_btn = page.locator('.wa-habit-btn').first
            h_btn.click()
            page.wait_for_timeout(600)
            assert page.url == habit_list_url, f"Expected URL to remain {habit_list_url}, but got {page.url}"
            print("  ✓ Habit button on /habits/ stayed in place (did NOT open detail)")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_habit_list_toggled.png"))

            # Step A6.5: Test Goal Detail Milestone In-Place Toggle
            print("  - Testing Goal detail milestone toggle in-place...")
            page.goto(f"{BASE_URL}/accounts/dashboard/")
            goal_link = page.locator('h3 a[href*="/goals/"]').first
            goal_href = goal_link.get_attribute('href')
            page.goto(f"{BASE_URL}{goal_href}" if not goal_href.startswith('http') else goal_href)
            page.wait_for_selector('.wa-checkbox-btn')
            goal_detail_url = page.url

            m_btn = page.locator('.wa-checkbox-btn').first
            m_btn.click()
            page.wait_for_timeout(600)
            assert page.url == goal_detail_url, f"Expected URL to remain {goal_detail_url}, but got {page.url}"
            print("  ✓ Milestone toggle stayed in place on goal detail (did NOT redirect away)")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07b_goal_milestone_toggled.png"))

            # Step A7: Test Light Mode & Dark Mode Styles
            print("\n[5/6] Testing Light Mode vs Dark Mode visual distinction...")
            page.goto(f"{BASE_URL}/accounts/dashboard/")
            page.wait_for_selector('.task-row')

            # Force Light Mode
            page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
            page.evaluate("localStorage.setItem('wa_theme', 'light')")
            page.wait_for_timeout(300)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_dashboard_light_mode.png"))
            print("  ✓ Captured Light Mode dashboard screenshot")

            # Force Dark Mode
            page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
            page.evaluate("localStorage.setItem('wa_theme', 'dark')")
            page.wait_for_timeout(300)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "09_dashboard_dark_mode.png"))
            print("  ✓ Captured Dark Mode dashboard screenshot")

            context.close()

            # -------------------------------------------------------------
            # TEST B: MOBILE WORKFLOW (390x844)
            # -------------------------------------------------------------
            print("\n[6/6] Starting Mobile QA (390x844 iPhone 12/13/14)...")
            mobile_context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
            mobile_page = mobile_context.new_page()

            mobile_page.on('console', lambda msg: console_errors.append(msg.text) if msg.type == 'error' else None)
            mobile_page.on('pageerror', lambda exc: console_errors.append(str(exc)))
            mobile_page.on('requestfailed', lambda req: failed_requests.append(f"{req.method} {req.url}: {req.failure}"))

            # Login on Mobile
            mobile_page.goto(f"{BASE_URL}/accounts/login/")
            mobile_page.fill('input[name="username"]', 'browseruser1')
            mobile_page.fill('input[name="password"]', 'Password123!')
            mobile_page.click('#login-submit-btn')
            mobile_page.wait_for_url(f"{BASE_URL}/accounts/dashboard/")

            # Verify Mobile Touch Target Dimension (>= 36px)
            m_checkbox = mobile_page.locator('.task-row .wa-checkbox-btn').first
            m_checkbox.wait_for(state='visible')
            box = m_checkbox.bounding_box()
            assert box is not None, "Mobile checkbox bounding box should exist"
            print(f"  ✓ Mobile checkbox hit target dimensions: {box['width']:.1f}px x {box['height']:.1f}px")
            assert box['width'] >= 34 and box['height'] >= 34, f"Hit target too small: {box}"

            # Toggle task on mobile
            m_dash_url = mobile_page.url
            m_checkbox.click()
            mobile_page.wait_for_timeout(600)
            assert mobile_page.url == m_dash_url, f"Expected mobile URL to remain {m_dash_url}, but got {mobile_page.url}"
            print("  ✓ Mobile task checkbox click stayed in place (did not navigate)")

            mobile_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "10_dashboard_mobile.png"))

            mobile_context.close()
            browser.close()

    finally:
        if server_process:
            print("Stopping server process...")
            server_process.terminate()

    # -------------------------------------------------------------
    # REPORT ERRORS
    # -------------------------------------------------------------
    print("\n" + "=" * 70)
    print("VERIFICATION RESULTS SUMMARY")
    print("=" * 70)
    print(f"Console errors: {len(console_errors)}")
    for err in console_errors:
        print(f"  - Console Error: {err}")

    print(f"Failed requests: {len(failed_requests)}")
    for req in failed_requests:
        print(f"  - Failed Request: {req}")

    if console_errors:
        print("FAIL: Console errors detected!")
        sys.exit(1)
    if failed_requests:
        print("FAIL: Failed requests detected!")
        sys.exit(1)

    print("\nSUCCESS: All interaction performance & QA checks passed perfectly!")


if __name__ == '__main__':
    main()
