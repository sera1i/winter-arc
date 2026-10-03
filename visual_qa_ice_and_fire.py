import os
import sys
from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots_ice_and_fire')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def run_qa():
    errors_found = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # 1. Test Viewports on Landing Page
        viewports = [
            {'name': '1920_desktop', 'width': 1920, 'height': 1080},
            {'name': '1280_laptop', 'width': 1280, 'height': 800},
            {'name': '768_tablet', 'width': 768, 'height': 1024},
            {'name': '390_mobile', 'width': 390, 'height': 844},
        ]

        for vp in viewports:
            print(f"Testing landing page on {vp['name']} ({vp['width']}x{vp['height']})...")
            context = browser.new_context(viewport={'width': vp['width'], 'height': vp['height']})
            page = context.new_page()

            page.on("console", lambda msg: errors_found.append(f"Console {msg.type}: {msg.text}") if msg.type in ['error', 'warning'] and 'favicon' not in msg.text else None)
            page.on("requestfailed", lambda req: failed_requests.append(f"Failed: {req.url} ({req.failure})") if 'favicon' not in req.url else None)

            response = page.goto(f"{BASE_URL}/", wait_until="networkidle")
            assert response.status == 200, f"Landing page returned status {response.status}"

            # Wait for loader fadeout
            page.wait_for_timeout(2500)

            shot_path = os.path.join(SCREENSHOTS_DIR, f"landing_{vp['name']}.png")
            page.screenshot(path=shot_path, full_page=True)
            print(f"Saved screenshot: {shot_path}")
            context.close()

        # 2. Test Authenticated Experience at 1920x1080
        print("Testing authenticated user journey at 1920x1080...")
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # Login page capture & action
        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "login_page.png"), full_page=True)

        page.fill('input[name="username"]', "warrior_qa")
        page.fill('input[name="password"]', "Password123!")
        page.click('main form button[type="submit"], div form:not([action*="logout"]) button[type="submit"]')
        page.wait_for_timeout(1500)
        print(f"Logged in, currently on: {page.url}")

        # Dashboard initial
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dashboard_view.png"), full_page=True)

        # Create an Arc
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arc_form.png"), full_page=True)
        page.fill('input[name="name"]', "The First Crucible")
        page.fill('textarea[name="objective"]', "100 days of relentless discipline, frost, and fire.")
        page.fill('input[name="start_date"]', "2026-10-01")
        page.fill('input[name="end_date"]', "2027-01-09")
        if page.query_selector('select[name="timezone"]'):
            page.select_option('select[name="timezone"]', 'UTC')
        page.click('main form button[type="submit"], div form:not([action*="logout"]) button[type="submit"]')
        page.wait_for_timeout(1500)

        # View Arcs list
        page.goto(f"{BASE_URL}/arcs/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arcs_list.png"), full_page=True)

        # Create a Habit
        page.goto(f"{BASE_URL}/habits/new/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "habit_form.png"), full_page=True)
        page.fill('input[name="name"]', "Morning Cold Exposure")
        page.fill('textarea[name="description"]', "5 minutes of cold water before dawn.")
        page.click('main form button[type="submit"], div form:not([action*="logout"]) button[type="submit"]')
        page.wait_for_timeout(1500)

        # View Habits list and light the beacon
        page.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "habits_list.png"), full_page=True)
        
        beacon_btn = page.query_selector('button:has-text("Light Beacon")')
        if beacon_btn:
            beacon_btn.click()
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "habits_beacon_lit.png"), full_page=True)

        # Create a Task
        page.goto(f"{BASE_URL}/tasks/new/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "task_form.png"), full_page=True)
        page.fill('input[name="title"]', "Review Seasonal Defense Map")
        page.fill('textarea[name="description"]', "Inspect boundaries and complete priority objectives.")
        page.select_option('select[name="priority"]', '1')
        page.click('main form button[type="submit"], div form:not([action*="logout"]) button[type="submit"]')
        page.wait_for_timeout(1500)

        # View Tasks list
        page.goto(f"{BASE_URL}/tasks/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "tasks_list.png"), full_page=True)

        # Return to Dashboard with populated metrics
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dashboard_active.png"), full_page=True)

        # Register page capture (logout first)
        page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "register_page.png"), full_page=True)

        # Styleguide & Motion Spec debug views
        page.goto(f"{BASE_URL}/_styleguide/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "debug_styleguide.png"), full_page=True)

        page.goto(f"{BASE_URL}/_motion-spec/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "debug_motion_spec.png"), full_page=True)

        context.close()
        browser.close()

    print("\nVisual QA Run Completed Successfully!")
    print(f"Screenshots saved to {SCREENSHOTS_DIR}")
    print(f"Console errors/warnings: {len(errors_found)}")
    for e in errors_found[:10]:
        print(f"  - {e}")
    print(f"Failed network requests: {len(failed_requests)}")
    for r in failed_requests:
        print(f"  - {r}")

if __name__ == '__main__':
    run_qa()
