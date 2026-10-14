import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

SERVER_PORT = "8049"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
PYTHON_BIN = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python"
OUTPUT_DIR = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/screenshots/visual_repair"
os.makedirs(OUTPUT_DIR, exist_ok=True)

server_process = subprocess.Popen(
    [PYTHON_BIN, "manage.py", "runserver", f"127.0.0.1:{SERVER_PORT}", "--noreload"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

ready = False
for _ in range(40):
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=1) as resp:
            if resp.status == 200:
                ready = True
                break
    except Exception:
        time.sleep(0.5)

if not ready:
    print("Server failed to start")
    if server_process:
        server_process.kill()
    sys.exit(1)

VIEWPORTS = [
    {"name": "1920x1080_desktop_large", "width": 1920, "height": 1080, "is_mobile": False},
    {"name": "1440x900_desktop_standard", "width": 1440, "height": 900, "is_mobile": False},
    {"name": "1024x768_tablet_landscape", "width": 1024, "height": 768, "is_mobile": False},
    {"name": "768x1024_tablet_portrait", "width": 768, "height": 1024, "is_mobile": True},
    {"name": "390x844_mobile_phone", "width": 390, "height": 844, "is_mobile": True},
    {"name": "360x800_small_mobile", "width": 360, "height": 800, "is_mobile": True},
]

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for vp in VIEWPORTS:
            print(f"Testing viewport: {vp['name']} ({vp['width']}x{vp['height']})...")
            context = browser.new_context(
                viewport={"width": vp["width"], "height": vp["height"]},
                is_mobile=vp["is_mobile"]
            )
            page = context.new_page()
            page.goto(f"{BASE_URL}/", wait_until="networkidle")
            
            # Wait for loader to finish
            page.wait_for_timeout(1000)

            # 1. Capture Header & Nav Scrolled State
            page.evaluate("window.scrollTo(0, 300)")
            page.wait_for_timeout(300)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{vp['name']}_header_scrolled.png"))

            # 2. Capture Anchor Jump to #features
            page.evaluate("document.getElementById('features').scrollIntoView()")
            page.wait_for_timeout(400)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{vp['name']}_features_anchor.png"))

            # 3. Capture Knight Quote Banner In-View
            page.evaluate("window.scrollBy(0, 320)")
            page.wait_for_timeout(400)
            page.screenshot(path=os.path.join(OUTPUT_DIR, f"{vp['name']}_knight_banner.png"))

            # 4. If mobile, test hamburger menu open
            if vp["is_mobile"]:
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(200)
                menu_btn = page.query_selector("#mobile-menu-btn")
                if menu_btn and menu_btn.is_visible():
                    menu_btn.click()
                    page.wait_for_timeout(300)
                    page.screenshot(path=os.path.join(OUTPUT_DIR, f"{vp['name']}_drawer_open.png"))

            context.close()

        # Capture complete full-page references for Desktop 1440 and Mobile 390
        print("Capturing full-page references...")
        ctx_d = browser.new_context(viewport={"width": 1440, "height": 900})
        pg_d = ctx_d.new_page()
        pg_d.goto(f"{BASE_URL}/", wait_until="networkidle")
        pg_d.wait_for_timeout(1000)
        pg_d.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        pg_d.wait_for_timeout(500)
        pg_d.evaluate("window.scrollTo(0, 0)")
        pg_d.wait_for_timeout(300)
        pg_d.screenshot(path=os.path.join(OUTPUT_DIR, "full_page_desktop_1440.png"), full_page=True)
        ctx_d.close()

        ctx_m = browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        pg_m = ctx_m.new_page()
        pg_m.goto(f"{BASE_URL}/", wait_until="networkidle")
        pg_m.wait_for_timeout(1000)
        pg_m.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        pg_m.wait_for_timeout(500)
        pg_m.evaluate("window.scrollTo(0, 0)")
        pg_m.wait_for_timeout(300)
        pg_m.screenshot(path=os.path.join(OUTPUT_DIR, "full_page_mobile_390.png"), full_page=True)
        ctx_m.close()

        browser.close()
        print("Visual verification screenshots captured successfully.")

finally:
    if server_process:
        server_process.terminate()
        server_process.wait()
