import os
import sys
import time
import subprocess
import urllib.request
from playwright.sync_api import sync_playwright

BASE_URL = 'http://127.0.0.1:8000'

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def inspect():
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Launching Django dev server...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=25):
            print("Server failed to start")
            sys.exit(1)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"{BASE_URL}/accounts/login/")
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')
            page.click('button[type="submit"]')
            page.wait_for_load_state('networkidle')
            
            elements = {
                'Tier 1': 'text=Tier',
                '0 remaining': 'text=remaining',
                '0 active arcs': 'text=active arcs',
                'Habits Today /': 'text=/',
                'Strategic Objectives': 'text=Strategic Objectives',
                'Goals & Milestones': '#goals-heading',
                'View in Arcs': 'text=View in Arcs',
                'Nav Dashboard': '#global-navbar >> text=Dashboard',
                'Nav Arcs': '#global-navbar >> text=Arcs',
                'Nav Logout': '#global-navbar >> text=Log out',
            }
            print('=== DASHBOARD COMPUTED STYLES ===')
            for label, sel in elements.items():
                loc = page.locator(sel).first
                if loc.count() > 0:
                    color = loc.evaluate('el => window.getComputedStyle(el).color')
                    font_size = loc.evaluate('el => window.getComputedStyle(el).fontSize')
                    opacity = loc.evaluate('el => window.getComputedStyle(el).opacity')
                    print(f'{label}: color={color}, size={font_size}, opacity={opacity}')
                else:
                    print(f'{label}: NOT FOUND')
                    
            # Check Analytics
            page.goto(f"{BASE_URL}/analytics/")
            page.wait_for_load_state('networkidle')
            analytics_elements = {
                'Current Standing': 'text=Current Standing',
                'Verified Total': 'text=Verified Total',
                'Tier I': 'text=Tier I',
                'Tier I XP range': 'text=0 – 299 XP',
                'Next:': 'text=Next:',
                'tier progression': 'text=tier progression',
                'Task Success Rate': 'text=Task Success Rate',
                '1 done / 1 total': 'text=done /',
                'Historical Best': 'text=Historical Best',
                'habit beacons lit': 'text=habit beacon',
                'Total Tasks This Week': 'text=Total Tasks This Week',
                'Supporting desc': 'p:has-text("Every statistic")',
            }
            print('\n=== ANALYTICS COMPUTED STYLES ===')
            for label, sel in analytics_elements.items():
                loc = page.locator(sel).first
                if loc.count() > 0:
                    color = loc.evaluate('el => window.getComputedStyle(el).color')
                    font_size = loc.evaluate('el => window.getComputedStyle(el).fontSize')
                    opacity = loc.evaluate('el => window.getComputedStyle(el).opacity')
                    print(f'{label}: color={color}, size={font_size}, opacity={opacity}')
                else:
                    print(f'{label}: NOT FOUND')
            browser.close()
    finally:
        if server_process:
            server_process.terminate()

if __name__ == '__main__':
    inspect()
