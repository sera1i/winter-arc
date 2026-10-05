"""
Verification script for popup alert auto-hide after 5 seconds.
"""
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
                if response.status in (200, 302):
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def main():
    print("=" * 60)
    print("TESTING POPUP ALERT AUTO-HIDE AFTER 5 SECONDS")
    print("=" * 60)

    # 1. Prepare fixtures
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # 2. Check/Launch server
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Starting dev server...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=20):
            print("ERROR: Dev server failed to start.")
            if server_process:
                server_process.terminate()
            sys.exit(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Log in
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            print("[AUTH] Logged in successfully.")

            # Navigate to profile to trigger a flash message
            page.goto(f"{BASE_URL}/accounts/profile/", wait_until="networkidle")
            # Click Save Changes to generate messages.success
            page.click('button:has-text("Save Changes")')
            page.wait_for_load_state("networkidle")

            t0 = time.time()
            # Verify popup alert is immediately visible
            alert_elem = page.locator('#flash-messages-container')
            alert_elem.wait_for(state='visible', timeout=3000)
            is_visible_0 = alert_elem.is_visible()
            print(f"[T+0.0s] Popup alert visible: {is_visible_0} (Text: '{alert_elem.inner_text().strip()}')")
            assert is_visible_0, "Popup alert should be visible immediately after appearing!"

            img1 = os.path.join(SCREENSHOTS_DIR, "alert_01_visible_immediate.png")
            page.screenshot(path=img1)
            print(f"Captured: {img1}")

            # Wait 2.5 seconds (still well within the 5-second window)
            time.sleep(2.5)
            is_visible_2_5 = alert_elem.is_visible()
            elapsed_2_5 = time.time() - t0
            print(f"[T+{elapsed_2_5:.1f}s] Popup alert still visible: {is_visible_2_5}")
            assert is_visible_2_5, "Popup alert must still be visible at ~2.5s!"

            img2 = os.path.join(SCREENSHOTS_DIR, "alert_02_still_visible_2_5s.png")
            page.screenshot(path=img2)
            print(f"Captured: {img2}")

            # Wait remaining time to pass 5.6 seconds (5s timeout + 0.5s transition)
            time.sleep(3.2)
            elapsed_final = time.time() - t0
            
            # Check whether it is removed from DOM or detached/hidden
            count = page.locator('#flash-messages-container').count()
            is_visible_final = False
            if count > 0:
                is_visible_final = alert_elem.is_visible()

            print(f"[T+{elapsed_final:.1f}s] Popup alert count in DOM: {count}, visible: {is_visible_final}")
            assert not is_visible_final or count == 0, f"Popup alert should be hidden/removed after 5 seconds! (count={count}, visible={is_visible_final})"

            img3 = os.path.join(SCREENSHOTS_DIR, "alert_03_hidden_after_5s.png")
            page.screenshot(path=img3)
            print(f"Captured: {img3}")

            browser.close()
            print("=" * 60)
            print("SUCCESS: POPUP ALERT AUTO-HIDE (5s) VERIFIED IN BROWSER!")
            print("=" * 60)

    finally:
        if server_process:
            server_process.terminate()


if __name__ == '__main__':
    main()
