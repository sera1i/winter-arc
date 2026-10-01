import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://127.0.0.1:8004/")
        page.wait_for_selector('text=ENTER THE SHADOWS', timeout=15000, state='visible')
        time.sleep(1) # just in case
        page.screenshot(path="kage_screenshot_loaded.png")
        print("Screenshot saved to kage_screenshot_loaded.png")
        browser.close()
run()
