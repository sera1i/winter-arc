import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8025"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/ui_ux_redesign/screenshots/phase_4"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

python_bin = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python"

print("Starting Django server on port", SERVER_PORT)
server_process = subprocess.Popen(
    [
        python_bin,
        "manage.py",
        "runserver",
        f"127.0.0.1:{SERVER_PORT}",
        "--noreload"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

started = False
for i in range(30):
    try:
        resp = urllib.request.urlopen(f"{BASE_URL}/accounts/login/", timeout=1)
        if resp.status == 200:
            started = True
            print("Server is responsive!")
            break
    except Exception:
        time.sleep(1)

if not started:
    print("Server failed to respond in 30 seconds.")
    server_process.kill()
    sys.exit(1)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # -------------------------------------------------------------
        # 1. Desktop Viewport (1440x900)
        # -------------------------------------------------------------
        print("Capturing Desktop screens...")
        desktop_context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False
        )
        page = desktop_context.new_page()

        # Login first
        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page.fill('input[name="username"]', 'browseruser1')
        page.fill('input[name="password"]', 'Password123!')
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(500)

        # Capture Dashboard Desktop (Light)
        page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('light') : document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('winter_arc_theme', 'light');")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_desktop_light.png", full_page=False)
        print("Captured: dashboard_desktop_light.png")

        # Capture Dashboard Desktop (Dark)
        page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_desktop_dark.png", full_page=False)
        print("Captured: dashboard_desktop_dark.png")

        # Verify action: Habit check-in
        habit_btn = page.query_selector('.wa-habit-btn-pending')
        if habit_btn:
            habit_btn.click()
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(400)
            page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_desktop_habit_checked.png", full_page=False)
            print("Captured: dashboard_desktop_habit_checked.png")

        desktop_context.close()

        # -------------------------------------------------------------
        # 2. Mobile Viewport (390x844)
        # -------------------------------------------------------------
        print("Capturing Mobile screens...")
        mobile_context = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        mobile_page = mobile_context.new_page()

        # Login on mobile
        mobile_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        mobile_page.fill('input[name="username"]', 'browseruser1')
        mobile_page.fill('input[name="password"]', 'Password123!')
        mobile_page.click('button[type="submit"]')
        mobile_page.wait_for_load_state("networkidle")
        mobile_page.wait_for_timeout(500)

        # Mobile Light
        mobile_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('light') : document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('winter_arc_theme', 'light');")
        mobile_page.wait_for_timeout(400)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_mobile_light.png", full_page=False)
        print("Captured: dashboard_mobile_light.png")

        # Mobile Dark
        mobile_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        mobile_page.wait_for_timeout(400)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_mobile_dark.png", full_page=False)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_mobile_dark_full.png", full_page=True)
        print("Captured: dashboard_mobile_dark.png & full")

        mobile_context.close()

        # Desktop Full
        desktop_context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = desktop_context.new_page()
        page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page.fill('input[name="username"]', 'browseruser1')
        page.fill('input[name="password"]', 'Password123!')
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")
        page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        page.wait_for_timeout(400)
        page.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_desktop_dark_full.png", full_page=True)
        desktop_context.close()

        browser.close()
        print("All Phase 4 screenshots captured successfully!")

finally:
    print("Terminating test server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
