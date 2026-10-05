import os
import sys
import time
import subprocess
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots_theme_qa')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def run_browser_verification():
    print("=" * 70)
    print("STARTING PLAYWRIGHT LIGHT/DARK CONTRAST & BACK-NAV QA SUITE")
    print("=" * 70)

    # 1. Run fixtures prep
    print("[INIT] Ensuring test user and entity fixtures...")
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # 2. Fetch exact entity IDs directly via Django ORM before launching Playwright
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from arcs.models import Arc
    from goals.models import Goal
    from tasks.models import Task
    from habits.models import Habit
    from journal.models import JournalEntry

    u = get_user_model().objects.get(username='browseruser1')
    arc_obj = Arc.objects.filter(user=u).first()
    goal_obj = Goal.objects.filter(user=u).first()
    task_obj = Task.objects.filter(user=u).first()
    habit_obj = Habit.objects.filter(user=u).first()
    journal_obj = JournalEntry.objects.filter(user=u).first()

    arc_url = f"/arcs/{arc_obj.pk}/"
    goal_url = f"/goals/{goal_obj.pk}/"
    task_url = f"/tasks/{task_obj.pk}/"
    habit_url = f"/habits/{habit_obj.pk}/"
    journal_url = f"/journal/{journal_obj.pk}/"
    print(f"Entities loaded: arc={arc_url}, goal={goal_url}, task={task_url}, habit={habit_url}, journal={journal_url}")

    # 3. Launch Django dev server if not already running
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Launching Django dev server on port 8000...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=25):
            print("ERROR: Server failed to start in 25 seconds.")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print("Django server ready.")
    else:
        print("Django server already running on port 8000.")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()

            # -------------------------------------------------------------
            # STEP 1: Verify Landing Page & Loader Isolation
            # -------------------------------------------------------------
            print("\n[STEP 1] Testing Landing Page & Loader Isolation...")
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            
            html_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            print(f"Landing page <html> data-theme attribute: {html_theme} (Expected: None)")
            assert html_theme is None, f"Landing page must NOT have data-theme! Found: {html_theme}"

            toggle_count = page.locator('#theme-toggle-btn').count()
            print(f"Landing page #theme-toggle-btn count: {toggle_count} (Expected: 0)")
            assert toggle_count == 0, "Theme toggle button should NOT exist on landing page!"

            loader_count = page.locator('#wa-loader').count()
            assert loader_count >= 1, "Landing page loader must remain intact!"

            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_landing_page_isolated.png"), full_page=True)
            print("Saved screenshot: 01_landing_page_isolated.png")

            # -------------------------------------------------------------
            # STEP 2: Authenticate and Verify Default Light Mode
            # -------------------------------------------------------------
            print("\n[STEP 2] Authenticating and Testing Default Light Mode...")
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            assert "/accounts/dashboard/" in page.url or "/dashboard" in page.url
            
            theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            print(f"Dashboard <html> data-theme attribute: {theme} (Expected: 'light')")
            assert theme == "light", f"Default theme must be 'light'! Got: {theme}"

            # Check button text color: must be bone/white (#faf9f6 or similar), NOT dark ink!
            btn_color = page.evaluate("""
                () => {
                    const btn = document.querySelector('.btn-primary');
                    return btn ? window.getComputedStyle(btn).color : null;
                }
            """)
            print(f".btn-primary text color in Light Mode: {btn_color}")
            # rgb(250, 249, 246) is #FAF9F6
            assert btn_color in ['rgb(250, 249, 246)', 'rgb(255, 255, 255)'], f"Button text contrast failure! Found: {btn_color}"

            # -------------------------------------------------------------
            # STEP 3: Capture Required LIGHT Pages
            # -------------------------------------------------------------
            print("\n[STEP 3] Capturing Required LIGHT Pages...")

            # 1. Dashboard
            page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_dashboard.png"), full_page=True)
            print("Saved screenshot: light_dashboard.png")

            # Arc detail
            page.goto(f"{BASE_URL}{arc_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').count() >= 1, "wa-back-link missing on Arc detail!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_arc_detail.png"), full_page=True)
            print(f"Saved screenshot: light_arc_detail.png ({page.url})")

            # Goal detail
            page.goto(f"{BASE_URL}{goal_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').count() >= 1, "wa-back-link missing on Goal detail!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_goal_detail.png"), full_page=True)
            print(f"Saved screenshot: light_goal_detail.png ({page.url})")

            # Task detail
            page.goto(f"{BASE_URL}{task_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').count() >= 1, "wa-back-link missing on Task detail!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_task_detail.png"), full_page=True)
            print(f"Saved screenshot: light_task_detail.png ({page.url})")

            # Habit detail
            page.goto(f"{BASE_URL}{habit_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').count() >= 1, "wa-back-link missing on Habit detail!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_habit_detail.png"), full_page=True)
            print(f"Saved screenshot: light_habit_detail.png ({page.url})")

            # Journal detail
            page.goto(f"{BASE_URL}{journal_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').count() >= 1, "wa-back-link missing on Journal detail!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_journal_detail.png"), full_page=True)
            print(f"Saved screenshot: light_journal_detail.png ({page.url})")

            # Analytics
            page.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_analytics.png"), full_page=True)
            print("Saved screenshot: light_analytics.png")

            # Notifications
            page.goto(f"{BASE_URL}/notifications/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "light_notifications.png"), full_page=True)
            print("Saved screenshot: light_notifications.png")

            # -------------------------------------------------------------
            # STEP 4: Switch to Dark Mode & Capture Required DARK Pages
            # -------------------------------------------------------------
            print("\n[STEP 4] Switching to Dark Mode & Capturing Required DARK Pages...")
            toggle = page.locator('#theme-toggle-btn')
            toggle.click()
            time.sleep(0.5)

            dark_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
            assert dark_theme == "dark", f"Expected dark theme! Got: {dark_theme}"

            # Dashboard Dark
            page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dark_dashboard.png"), full_page=True)
            print("Saved screenshot: dark_dashboard.png")

            # Arc detail Dark
            page.goto(f"{BASE_URL}{arc_url}", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dark_arc_detail.png"), full_page=True)
            print("Saved screenshot: dark_arc_detail.png")

            # Task detail Dark
            page.goto(f"{BASE_URL}{task_url}", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dark_task_detail.png"), full_page=True)
            print("Saved screenshot: dark_task_detail.png")

            # Analytics Dark
            page.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "dark_analytics.png"), full_page=True)
            print("Saved screenshot: dark_analytics.png")

            # -------------------------------------------------------------
            # STEP 5: Mobile Viewport Testing (Light & Dark)
            # -------------------------------------------------------------
            print("\n[STEP 5] Testing Mobile Viewport (390x844)...")
            page.set_viewport_size({'width': 390, 'height': 844})

            # Mobile Dashboard Dark
            page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_dashboard_dark.png"))
            print("Saved screenshot: mobile_dashboard_dark.png")

            # Mobile Detail Page Dark
            page.goto(f"{BASE_URL}{arc_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').is_visible(), "Back link not visible on mobile!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_detail_dark.png"))
            print("Saved screenshot: mobile_detail_dark.png")

            # Switch back to light mode using mobile drawer
            page.locator('#mobile-menu-btn').click()
            page.wait_for_selector('#mobile-menu:not(.hidden)', timeout=5000)
            page.locator('#mobile-theme-toggle-btn').click()
            time.sleep(0.5)

            reloaded_light = page.evaluate("document.documentElement.getAttribute('data-theme')")
            assert reloaded_light == "light", f"Mobile toggle to light failed! Got {reloaded_light}"

            # Mobile Dashboard Light
            page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_dashboard_light.png"))
            print("Saved screenshot: mobile_dashboard_light.png")

            # Mobile Detail Page Light
            page.goto(f"{BASE_URL}{arc_url}", wait_until="networkidle")
            assert page.locator('.wa-back-link').is_visible(), "Back link not visible on mobile light!"
            page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "mobile_detail_light.png"))
            print("Saved screenshot: mobile_detail_light.png")

            # Verify Back Link click works
            back_btn = page.locator('.wa-back-link')
            back_btn.click()
            page.wait_for_load_state("networkidle")
            print(f"After clicking back link, URL is: {page.url}")
            assert "/arcs/" in page.url, f"Expected navigation to /arcs/, got {page.url}"

            browser.close()

        print("\n" + "=" * 70)
        print("ALL BROWSER THEME & BACK-NAV CHECKS PASSED PERFECTLY!")
        print("=" * 70)

    finally:
        if server_process:
            print("Terminating Django test server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("Django test server terminated.")

if __name__ == '__main__':
    run_browser_verification()
