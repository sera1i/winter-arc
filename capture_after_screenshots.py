import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

SERVER_PORT = "8015"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/audit_screenshots_after"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

import urllib.request

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
    time.sleep(5)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Test Light Mode (Default)
        ctx_light = browser.new_context(viewport={"width": 1440, "height": 900})
        page_light = ctx_light.new_page()
        
        # Landing Page (Desktop)
        page_light.goto(f"{BASE_URL}/", wait_until="networkidle")
        time.sleep(1)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/01_landing_desktop_after.png")

        # Login Page before auth
        page_light.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/02_login_desktop_after.png")
        
        # Register Page
        page_light.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/02_register_desktop_after.png")
        
        # Perform Login
        page_light.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_light.fill('input[name="username"]', 'browseruser1')
        page_light.fill('input[name="password"]', 'Password123!')
        page_light.click('button[type="submit"]')
        page_light.wait_for_url("**/dashboard/**")
        page_light.wait_for_load_state("networkidle")
        
        # Dashboard Light
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_light_after.png")
        
        # Presets Library Light
        page_light.goto(f"{BASE_URL}/arcs/presets/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/04_arcs_presets_after.png")
        
        # Arcs Detail Light
        page_light.goto(f"{BASE_URL}/arcs/66/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/05_arc_detail_light_after.png")
        
        # Habits Light
        page_light.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_light_after.png")
        
        # Analytics Light
        page_light.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/09_analytics_light_after.png")
        
        # Journal Light
        page_light.goto(f"{BASE_URL}/journal/", wait_until="networkidle")
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/08_journal_light_after.png")
        
        ctx_light.close()
        
        # Test Dark Mode
        ctx_dark = browser.new_context(viewport={"width": 1440, "height": 900})
        page_dark = ctx_dark.new_page()
        page_dark.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_dark.fill('input[name="username"]', 'browseruser1')
        page_dark.fill('input[name="password"]', 'Password123!')
        page_dark.click('button[type="submit"]')
        page_dark.wait_for_url("**/dashboard/**")
        
        # Toggle Dark theme
        page_dark.click('#theme-toggle-btn')
        time.sleep(1)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_dark_after.png")
        
        # Tasks Dark
        page_dark.goto(f"{BASE_URL}/tasks/", wait_until="networkidle")
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/06_tasks_dark_after.png")
        
        # Habits Dark
        page_dark.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_dark_after.png")
        
        # Analytics Dark
        page_dark.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/09_analytics_dark_after.png")
        
        # Focus Mode
        page_dark.goto(f"{BASE_URL}/focus/", wait_until="networkidle")
        time.sleep(1.5)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/10_focus_after.png")
        
        ctx_dark.close()
        
        # Test Mobile Viewport (iPhone 14/15 390x844)
        ctx_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        page_mob = ctx_mobile.new_page()
        
        # Mobile Login
        page_mob.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/02_login_mobile_after.png")
        
        # Mobile Auth & Dashboard
        page_mob.fill('input[name="username"]', 'browseruser1')
        page_mob.fill('input[name="password"]', 'Password123!')
        page_mob.click('button[type="submit"]')
        page_mob.wait_for_url("**/dashboard/**")
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_mobile_after.png")
        
        # Mobile Habits
        page_mob.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_mobile_after.png")
        
        ctx_mobile.close()
        
        browser.close()
        print("All after-redesign screenshots captured successfully.")
finally:
    server_process.terminate()
    server_process.wait()
