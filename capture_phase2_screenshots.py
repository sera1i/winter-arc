import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8022"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/ui_ux_redesign/screenshots/phase_2"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

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
        page_d.screenshot(path=f"{SCREENSHOT_DIR}/landing_desktop.png")

        # 2. Authenticated Dashboard (Default Light theme)
        page_d.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_d.fill('input[name="username"]', 'browseruser1')
        page_d.fill('input[name="password"]', 'Password123!')
        page_d.click('button[type="submit"]')
        page_d.wait_for_url("**/dashboard/**")
        page_d.wait_for_load_state("networkidle")
        time.sleep(1)
        page_d.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_desktop_light.png")

        # 3. Authenticated Dashboard (Dark theme)
        page_d.click('#theme-toggle-btn')
        time.sleep(1)
        page_d.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_desktop_dark.png")

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
        page_m.screenshot(path=f"{SCREENSHOT_DIR}/landing_mobile.png")

        # 2. Authenticated Dashboard Mobile (Light theme)
        page_m.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        page_m.fill('input[name="username"]', 'browseruser1')
        page_m.fill('input[name="password"]', 'Password123!')
        page_m.click('button[type="submit"]')
        page_m.wait_for_url("**/dashboard/**")
        page_m.wait_for_load_state("networkidle")
        time.sleep(1)
        page_m.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_mobile_light.png")

        # 3. Authenticated Dashboard Mobile (Dark theme)
        # Open mobile drawer to click mobile theme toggle
        page_m.click('#mobile-menu-btn')
        time.sleep(0.5)
        page_m.click('#mobile-theme-toggle-btn')
        time.sleep(0.5)
        page_m.click('#mobile-menu-btn') # close drawer
        time.sleep(1)
        page_m.screenshot(path=f"{SCREENSHOT_DIR}/dashboard_mobile_dark.png")

        ctx_m.close()
        browser.close()
        print("Phase 2 screenshots captured successfully!")

finally:
    server_process.terminate()
    server_process.wait()
