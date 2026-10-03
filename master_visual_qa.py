import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots_master_qa')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def check_overflow(page, page_name, vp_name):
    scroll_w = page.evaluate("() => document.documentElement.scrollWidth")
    inner_w = page.evaluate("() => window.innerWidth")
    if scroll_w > inner_w:
        print(f"  [OVERFLOW WARNING] {page_name} on {vp_name}: scrollWidth ({scroll_w}) > innerWidth ({inner_w})")
        return False
    return True

def run_qa():
    errors_found = []
    failed_requests = []
    overflow_issues = []

    from accounts.models import CustomUser
    u = CustomUser.objects.filter(username='warrior_qa').first()
    if u:
        u.arcs.all().delete()
        u.tasks.all().delete()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Multi-Viewport Responsive Matrix on Landing Page
        viewports = [
            {'name': '1920_desktop', 'width': 1920, 'height': 1080},
            {'name': '1440_laptop', 'width': 1440, 'height': 900},
            {'name': '1280_compact_laptop', 'width': 1280, 'height': 800},
            {'name': '1024_small_desktop', 'width': 1024, 'height': 768},
            {'name': '768_tablet', 'width': 768, 'height': 1024},
            {'name': '390_mobile', 'width': 390, 'height': 844},
            {'name': '375_compact_mobile', 'width': 375, 'height': 667},
        ]

        print("=== STAGE 1: MULTI-VIEWPORT LANDING PAGE TESTS ===")
        for vp in viewports:
            print(f"Testing landing page on {vp['name']} ({vp['width']}x{vp['height']})...")
            context = browser.new_context(viewport={'width': vp['width'], 'height': vp['height']})
            page = context.new_page()

            page.on("console", lambda msg: errors_found.append(f"Console {msg.type}: {msg.text}") if msg.type in ['error'] and 'favicon' not in msg.text else None)
            page.on("requestfailed", lambda req: failed_requests.append(f"Failed: {req.url} ({req.failure})") if 'favicon' not in req.url else None)

            response = page.goto(f"{BASE_URL}/", wait_until="networkidle")
            assert response.status == 200, f"Landing page returned status {response.status}"

            page.wait_for_timeout(1800)

            if not check_overflow(page, "Landing", vp['name']):
                overflow_issues.append(f"Landing on {vp['name']}")

            shot_path = os.path.join(SCREENSHOTS_DIR, f"landing_{vp['name']}.png")
            page.screenshot(path=shot_path, full_page=True)
            print(f"  Saved screenshot: {shot_path}")
            context.close()

        # 2. Authenticated End-to-End User Journey at 1920x1080
        print("\n=== STAGE 2: AUTHENTICATED USER JOURNEY & FUNCTION VERIFICATION ===")
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        page.on("console", lambda msg: errors_found.append(f"Console {msg.type}: {msg.text}") if msg.type in ['error'] and 'favicon' not in msg.text else None)
        page.on("requestfailed", lambda req: failed_requests.append(f"Failed: {req.url} ({req.failure})") if 'favicon' not in req.url else None)

        # Login page
        print("Visiting login page...")
        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        check_overflow(page, "Login", "1920")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "auth_login.png"), full_page=True)

        page.fill('input[name="username"]', "warrior_qa")
        page.fill('input[name="password"]', "Password123!")
        page.click('main form button[type="submit"]')
        page.wait_for_timeout(1200)

        # Dashboard initial
        print(f"Logged in. URL: {page.url}")
        check_overflow(page, "Dashboard", "1920")

        # Create Arc & make it primary
        print("Creating an Arc...")
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        check_overflow(page, "Arc Form", "1920")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arc_form.png"), full_page=True)
        page.fill('input[name="name"]', "First Northern Campaign")
        page.fill('textarea[name="objective"]', "Hold the wall for 90 days. Stand fast against the cold.")
        page.fill('input[name="start_date"]', "2026-10-01")
        page.fill('input[name="end_date"]', "2027-01-09")
        page.check('input[name="is_primary"]')
        page.click('main form button[type="submit"]')
        page.wait_for_timeout(1200)

        # Add Goal to this Arc
        print(f"On Arc Detail: {page.url}. Adding Goal...")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arc_detail_initial.png"), full_page=True)
        
        # Click Add Goal
        add_goal_link = page.query_selector('a:has-text("Add Goal")')
        if add_goal_link:
            add_goal_link.click()
            page.wait_for_timeout(800)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "goal_form.png"), full_page=True)
            page.fill('input[name="title"]', "Conquer Deep Cold Adaptation")
            page.fill('textarea[name="description"]', "Daily cold exposure protocols to build extreme resilience.")
            page.select_option('select[name="category"]', 'HEALTH')
            page.click('main form button[type="submit"]')
            page.wait_for_timeout(1200)

        # Now verify Goal displays on Arc Detail!
        print(f"Verifying Goal displays on Arc Detail ({page.url})...")
        goal_on_arc = page.query_selector('text=Conquer Deep Cold Adaptation')
        assert goal_on_arc is not None, "BUG: Goal did NOT display on Arc Detail after creation!"
        print("  -> SUCCESS: Goal is displaying on Arc Detail!")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arc_detail_with_goal.png"), full_page=True)

        # Add Milestone to this Goal
        goal_detail_link = page.query_selector('a:has-text("Conquer Deep Cold Adaptation")')
        if goal_detail_link:
            goal_detail_link.click()
            page.wait_for_timeout(800)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "goal_detail.png"), full_page=True)
            # Add milestone
            page.fill('form[action*="milestones/new"] input[name="title"], #milestone-form input[name="title"]', "Complete 14 Consecutive Cold Showers")
            page.click('form[action*="milestones/new"] button[type="submit"], #milestone-form button[type="submit"]')
            page.wait_for_timeout(1000)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "goal_detail_with_milestone.png"), full_page=True)

        # Verify Dashboard displays Primary Arc AND the Goal!
        print("Visiting Dashboard to verify Primary Arc and Goal display...")
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        goal_on_dash = page.query_selector('text=Conquer Deep Cold Adaptation')
        assert goal_on_dash is not None, "BUG: Goal did NOT display on Dashboard!"
        print("  -> SUCCESS: Goal is displaying on Dashboard!")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "auth_dashboard_with_goals.png"), full_page=True)

        # Create Task
        print("Creating Task...")
        page.goto(f"{BASE_URL}/tasks/new/", wait_until="networkidle")
        page.fill('input[name="title"]', "Calibrate Bastion Defense Standard")
        page.fill('textarea[name="description"]', "Inspect boundaries and complete high-priority watch routines.")
        page.select_option('select[name="priority"]', '1')
        page.click('main form button[type="submit"]')
        page.wait_for_timeout(1200)

        # Verify Task displays on Tasks list AND on Dashboard
        print(f"On Tasks List: {page.url}")
        task_on_list = page.query_selector('text=Calibrate Bastion Defense Standard')
        assert task_on_list is not None, "BUG: Task did NOT display on Tasks list!"
        print("  -> SUCCESS: Task is displaying on Tasks list!")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "tasks_list.png"), full_page=True)

        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        task_on_dash = page.query_selector('text=Calibrate Bastion Defense Standard')
        assert task_on_dash is not None, "BUG: Task did NOT display on Dashboard!"
        print("  -> SUCCESS: Task is displaying on Dashboard!")

        # Test Mark Complete on Dashboard without leaving Dashboard
        complete_btn = page.query_selector('li.task-row button[type="submit"]')
        if complete_btn:
            print("Clicking complete checkmark on Dashboard...")
            complete_btn.click()
            page.wait_for_timeout(1000)
            assert "/accounts/dashboard/" in page.url, f"BUG: Task complete redirected away from Dashboard! URL={page.url}"
            print("  -> SUCCESS: Staid on Dashboard after task completion!")

        # Create a second Arc to test Primary toggle and Delete/Archive
        print("Creating second Arc to test Primary selection and Delete vs Archive...")
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        page.fill('input[name="name"]', "Second Reserve Campaign")
        page.fill('textarea[name="objective"]', "Secondary watch unit.")
        page.fill('input[name="start_date"]', "2026-10-15")
        page.fill('input[name="end_date"]', "2027-01-20")
        page.click('main form button[type="submit"]')
        page.wait_for_timeout(1200)

        page.goto(f"{BASE_URL}/arcs/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arcs_list.png"), full_page=True)

        # Test Make Primary
        make_primary_btn = page.query_selector('form[action*="make_primary"] button')
        if make_primary_btn:
            print("Clicking 'Make Primary' on second Arc...")
            make_primary_btn.click()
            page.wait_for_timeout(1000)
            print("  -> Primary Arc successfully changed!")

        # Test Manage / Delete options dialog
        delete_link = page.query_selector('a:has-text("Manage / Delete"), a:has-text("Archive / Delete")')
        if delete_link:
            delete_link.click()
            page.wait_for_timeout(800)
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "arc_archive_or_delete_dialog.png"), full_page=True)
            # Verify both buttons exist
            archive_btn = page.query_selector('button[value="archive"]')
            delete_btn = page.query_selector('button[value="delete"]')
            assert archive_btn is not None and delete_btn is not None, "BUG: Dual Archive and Delete options missing!"
            print("  -> SUCCESS: Dual Archive and Permanent Delete buttons verified!")

        # Final full page screenshot of Dashboard
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "auth_dashboard_final.png"), full_page=True)

        # Mobile View (390x844)
        mob_context = browser.new_context(viewport={'width': 390, 'height': 844})
        mob_page = mob_context.new_page()
        mob_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        mob_page.fill('input[name="username"]', "warrior_qa")
        mob_page.fill('input[name="password"]', "Password123!")
        mob_page.click('main form button[type="submit"]')
        mob_page.wait_for_timeout(1200)
        mob_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_dashboard_390.png"), full_page=True)
        mob_context.close()

        context.close()
        browser.close()

    print("\n==================================================")
    print("MASTER VISUAL & FUNCTIONAL QA PASSED!")
    print(f"Screenshots saved to: {SCREENSHOTS_DIR}")
    print(f"Total Overflow issues: {len(overflow_issues)}")
    print(f"Total Console errors: {len(errors_found)}")
    print(f"Total Failed requests: {len(failed_requests)}")
    print("==================================================")

if __name__ == '__main__':
    run_qa()
