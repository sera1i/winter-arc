import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8015"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/ui_ux_redesign/screenshots/phase_3"

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

# Wait for server to be responsive
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
        desktop_page = desktop_context.new_page()

        # Login Desktop
        desktop_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/login_desktop.png", full_page=False)
        print("Captured: login_desktop.png")

        # Test password toggle & error state
        desktop_page.fill('input[name="username"]', 'wronguser')
        desktop_page.fill('input[name="password"]', 'WrongSecretPassword123')
        
        # Toggle password
        desktop_page.click('#toggle-password')
        desktop_page.wait_for_timeout(300)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/login_desktop_password_revealed.png", full_page=False)
        print("Captured: login_desktop_password_revealed.png")

        # Submit invalid credentials to capture error state
        desktop_page.click('#login-submit-btn')
        desktop_page.wait_for_load_state("networkidle")
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/login_desktop_error_state.png", full_page=False)
        print("Captured: login_desktop_error_state.png")

        # Register Desktop
        desktop_page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/register_desktop.png", full_page=False)
        print("Captured: register_desktop.png")

        # Submit empty register form for error state
        desktop_page.click('#register-submit-btn')
        desktop_page.wait_for_load_state("networkidle")
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/register_desktop_error_state.png", full_page=False)
        print("Captured: register_desktop_error_state.png")

        # Dark theme captures (Desktop)
        desktop_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        desktop_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/login_desktop_dark.png", full_page=False)
        print("Captured: login_desktop_dark.png")

        desktop_page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        desktop_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        desktop_page.wait_for_timeout(500)
        desktop_page.screenshot(path=f"{SCREENSHOT_DIR}/register_desktop_dark.png", full_page=False)
        print("Captured: register_desktop_dark.png")

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

        # Login Mobile (Light)
        mobile_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        mobile_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('light') : document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('winter_arc_theme', 'light');")
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/login_mobile.png", full_page=False)
        print("Captured: login_mobile.png")

        # Login Mobile (Dark)
        mobile_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/login_mobile_dark.png", full_page=False)
        print("Captured: login_mobile_dark.png")

        # Register Mobile (Light)
        mobile_page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        mobile_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('light') : document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('winter_arc_theme', 'light');")
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/register_mobile.png", full_page=False)
        print("Captured: register_mobile.png")

        # Register Mobile (Dark)
        mobile_page.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        mobile_page.wait_for_timeout(500)
        mobile_page.screenshot(path=f"{SCREENSHOT_DIR}/register_mobile_dark.png", full_page=False)
        print("Captured: register_mobile_dark.png")

        mobile_context.close()
        browser.close()
        print("All Phase 3 screenshots captured successfully!")

finally:
    print("Terminating test server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        server_process.kill()
