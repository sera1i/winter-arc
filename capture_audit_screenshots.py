import os
import sys
import time
import subprocess
from playwright.sync_api import sync_playwright

SERVER_PORT = "8010"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/audit_screenshots"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# Start Django test server
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

time.sleep(3)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Viewports to test
        viewports = [
            ("desktop", 1440, 900),
            ("mobile", 390, 844)
        ]
        
        for vp_name, width, height in viewports:
            context = browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2 if vp_name == "mobile" else 1,
                is_mobile=True if vp_name == "mobile" else False,
                has_touch=True if vp_name == "mobile" else False,
            )
            page = context.new_page()
            
            # 1. Landing Page
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/01_landing_{vp_name}.png", full_page=False)
            
            # 2. Login Page
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/02_login_{vp_name}.png", full_page=False)
            
            # Perform Login
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')
            page.click('button[type="submit"]')
            page.wait_for_url("**/dashboard/**", timeout=10000)
            page.wait_for_load_state("networkidle")
            
            # 3. Dashboard (Populated)
            page.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_{vp_name}.png", full_page=False)
            
            # 4. Arcs List
            page.goto(f"{BASE_URL}/arcs/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/04_arcs_list_{vp_name}.png", full_page=False)
            
            # 5. Arc Detail
            page.goto(f"{BASE_URL}/arcs/66/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/05_arc_detail_{vp_name}.png", full_page=False)
            
            # 6. Tasks List
            page.goto(f"{BASE_URL}/tasks/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/06_tasks_{vp_name}.png", full_page=False)
            
            # 7. Habits List
            page.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_{vp_name}.png", full_page=False)
            
            # 8. Journal List
            page.goto(f"{BASE_URL}/journal/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/08_journal_{vp_name}.png", full_page=False)
            
            # 9. Analytics Dashboard
            page.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/09_analytics_{vp_name}.png", full_page=False)
            
            # 10. Focus Mode
            page.goto(f"{BASE_URL}/focus/", wait_until="networkidle")
            time.sleep(1)
            page.screenshot(path=f"{SCREENSHOT_DIR}/10_focus_{vp_name}.png", full_page=False)
            
            # 11. Profile & Settings
            page.goto(f"{BASE_URL}/accounts/profile/", wait_until="networkidle")
            page.screenshot(path=f"{SCREENSHOT_DIR}/11_profile_{vp_name}.png", full_page=False)
            
            context.close()
            print(f"Captured {vp_name} screenshots successfully.")
            
        browser.close()
finally:
    server_process.terminate()
    server_process.wait()
    print("Test server terminated.")
