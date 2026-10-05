import time
import subprocess
import sys
from playwright.sync_api import sync_playwright

import urllib.request

p = subprocess.Popen([sys.executable, 'manage.py', 'runserver', '127.0.0.1:8000', '--noreload'])

def wait_for_server(url, timeout=20):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200: return True
        except Exception:
            time.sleep(0.5)
    return False

wait_for_server('http://127.0.0.1:8000/accounts/login/')
try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        page.goto('http://127.0.0.1:8000/accounts/login/', wait_until='networkidle')
        page.fill('input[name="username"]', 'empty_user')
        page.fill('input[name="password"]', 'Password123!')
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')
        page.screenshot(path='screenshots_theme_qa/empty_dashboard_light.png', full_page=True)
        browser.close()
        print('Screenshot taken: empty_dashboard_light.png')
finally:
    p.terminate()
