import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8018"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR_DESKTOP = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/ui_ux_redesign/screenshots/desktop"
SCREENSHOT_DIR_MOBILE = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/ui_ux_redesign/screenshots/mobile"

os.makedirs(SCREENSHOT_DIR_DESKTOP, exist_ok=True)
os.makedirs(SCREENSHOT_DIR_MOBILE, exist_ok=True)

server_process = subprocess.Popen(
    [
        "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python",
        "manage.py",
        "runserver",
        f"127.0.0.1:{SERVER_PORT}",
        "--noreload"
    ],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

ready = False
for _ in range(40):
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health/", timeout=1) as resp:
            ready = True
            break
    except Exception:
        time.sleep(0.5)

if not ready:
    time.sleep(4)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # ---------------- DESKTOP (1440x900) ----------------
        ctx_d = browser.new_context(viewport={"width": 1440, "height": 900})
        page_d = ctx_d.new_page()

        # 1. Landing Page
        page_d.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(1)
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/01_landing.png")

        # 2. Login Page
        page_d.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/02_login.png")

        # 3. Registration Page
        page_d.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/03_register.png")

        # Authenticate
        page_d.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_d.fill('input[name="username"]', 'browseruser1')
        page_d.fill('input[name="password"]', 'Password123!')
        page_d.click('button[type="submit"]')
        page_d.wait_for_url("**/dashboard/**")
        page_d.wait_for_load_state("networkidle")

        # 4. Dashboard (Populated)
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/04_dashboard.png")

        # 5. Arc List
        page_d.goto(f"{BASE_URL}/arcs/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/05_arcs_list.png")

        # 6. Arc Presets
        page_d.goto(f"{BASE_URL}/arcs/presets/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/06_arcs_presets.png")

        # 7. Arc Detail
        page_d.goto(f"{BASE_URL}/arcs/66/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/07_arc_detail.png")

        # 8. Tasks
        page_d.goto(f"{BASE_URL}/tasks/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/08_tasks.png")

        # 9. Habits
        page_d.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/09_habits.png")

        # 10. Analytics
        page_d.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/10_analytics.png")

        # 11. Journal
        page_d.goto(f"{BASE_URL}/journal/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/11_journal.png")

        # 12. Focus Mode
        page_d.goto(f"{BASE_URL}/focus/", wait_until="networkidle")
        time.sleep(1.5)
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/12_focus_mode.png")

        # 13. Profile & Settings
        page_d.goto(f"{BASE_URL}/accounts/profile/", wait_until="networkidle")
        page_d.screenshot(path=f"{SCREENSHOT_DIR_DESKTOP}/13_profile.png")

        ctx_d.close()

        # ---------------- MOBILE (390x844) ----------------
        ctx_m = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_m = ctx_m.new_page()

        # 1. Landing Page Mobile
        page_m.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(1)
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/01_landing_mobile.png")

        # 2. Login Mobile
        page_m.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/02_login_mobile.png")

        # 3. Registration Mobile
        page_m.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/03_register_mobile.png")

        # Authenticate
        page_m.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_m.fill('input[name="username"]', 'browseruser1')
        page_m.fill('input[name="password"]', 'Password123!')
        page_m.click('button[type="submit"]')
        page_m.wait_for_url("**/dashboard/**")
        page_m.wait_for_load_state("networkidle")

        # 4. Dashboard Mobile
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/04_dashboard_mobile.png")

        # 5. Arc List Mobile
        page_m.goto(f"{BASE_URL}/arcs/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/05_arcs_list_mobile.png")

        # 6. Arc Presets Mobile
        page_m.goto(f"{BASE_URL}/arcs/presets/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/06_arcs_presets_mobile.png")

        # 7. Arc Detail Mobile
        page_m.goto(f"{BASE_URL}/arcs/66/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/07_arc_detail_mobile.png")

        # 8. Tasks Mobile
        page_m.goto(f"{BASE_URL}/tasks/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/08_tasks_mobile.png")

        # 9. Habits Mobile
        page_m.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/09_habits_mobile.png")

        # 10. Analytics Mobile
        page_m.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/10_analytics_mobile.png")

        # 11. Journal Mobile
        page_m.goto(f"{BASE_URL}/journal/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/11_journal_mobile.png")

        # 12. Focus Mode Mobile
        page_m.goto(f"{BASE_URL}/focus/", wait_until="networkidle")
        time.sleep(1.5)
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/12_focus_mode_mobile.png")

        # 13. Profile Mobile
        page_m.goto(f"{BASE_URL}/accounts/profile/", wait_until="networkidle")
        page_m.screenshot(path=f"{SCREENSHOT_DIR_MOBILE}/13_profile_mobile.png")

        ctx_m.close()
        browser.close()
        print("Fresh discovery screenshots captured successfully!")

finally:
    server_process.terminate()
    server_process.wait()
