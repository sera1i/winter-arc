import os
import sys
import time
import subprocess
import urllib.request
import django

# Set up Django environment for session creation
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.auth import SESSION_KEY, BACKEND_SESSION_KEY, HASH_SESSION_KEY, get_user_model
from playwright.sync_api import sync_playwright

User = get_user_model()
user = User.objects.get(username="browseruser1")
session = SessionStore()
session[SESSION_KEY] = str(user.pk)
session[BACKEND_SESSION_KEY] = 'django.contrib.auth.backends.ModelBackend'
session[HASH_SESSION_KEY] = user.get_session_auth_hash()
session.save()
from django.db import connection
connection.close()
print(f"Generated active session key: {session.session_key}")

session_cookie = {
    "name": "sessionid",
    "value": session.session_key,
    "domain": "127.0.0.1",
    "path": "/",
}

SERVER_PORT = "8058"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
SCREENSHOT_DIR = "/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/audit_screenshots_after"

os.makedirs(SCREENSHOT_DIR, exist_ok=True)

python_bin = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python"

print(f"Starting Django server on port {SERVER_PORT}...")
server_log = open("/mnt/c/Users/seral/OneDrive/Desktop/winter_arc/test_server.log", "w")
server_process = subprocess.Popen(
    [
        python_bin,
        "manage.py",
        "runserver",
        f"127.0.0.1:{SERVER_PORT}",
        "--noreload"
    ],
    stdout=server_log,
    stderr=server_log
)

ready = False
for i in range(70):
    if server_process.poll() is not None:
        print(f"Server exited prematurely with code {server_process.returncode}")
        server_log.close()
        sys.exit(1)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health/", timeout=1) as resp:
            if resp.status == 200:
                ready = True
                print("Server is responsive and ready!")
                break
    except Exception:
        time.sleep(0.5)

if not ready:
    print("Server failed to respond within 35s. Exiting.")
    server_process.kill()
    server_log.close()
    sys.exit(1)

print("Warming up views...")
try:
    req = urllib.request.Request(f"{BASE_URL}/accounts/dashboard/", headers={"Cookie": f"sessionid={session.session_key}"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        print("Warmup completed with status:", resp.status)
except Exception as e:
    print("Warmup exception (non-fatal):", e)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # =====================================================================
        # 1. Desktop Light Context
        # =====================================================================
        print("Capturing Desktop screens...")
        ctx_light = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx_light.add_init_script("try { window.localStorage.setItem('winter_arc_theme', 'light'); } catch(e){}")
        page_light = ctx_light.new_page()
        page_light.set_default_navigation_timeout(60000)

        # Landing Page (Desktop)
        page_light.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
        time.sleep(1)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/01_landing_desktop_after.png")
        print("  -> Captured: 01_landing_desktop_after.png")

        # Login Page before auth
        page_light.goto(f"{BASE_URL}/accounts/login/", wait_until="domcontentloaded")
        time.sleep(0.5)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/02_login_desktop_after.png")
        print("  -> Captured: 02_login_desktop_after.png")

        # Register Page
        page_light.goto(f"{BASE_URL}/accounts/register/", wait_until="domcontentloaded")
        time.sleep(0.5)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/02_register_desktop_after.png")
        print("  -> Captured: 02_register_desktop_after.png")

        # Inject authenticated session
        ctx_light.add_cookies([session_cookie])

        # Dashboard Light
        page_light.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="domcontentloaded")
        page_light.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('light') : document.documentElement.setAttribute('data-theme', 'light'); localStorage.setItem('winter_arc_theme', 'light');")
        time.sleep(0.8)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_light_after.png")
        print("  -> Captured: 03_dashboard_light_after.png")

        # Arcs List Light
        page_light.goto(f"{BASE_URL}/arcs/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/04_arcs_list_after.png")
        print("  -> Captured: 04_arcs_list_after.png")

        # Presets Library Light
        page_light.goto(f"{BASE_URL}/arcs/presets/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/04_arcs_presets_after.png")
        print("  -> Captured: 04_arcs_presets_after.png")

        # Arcs Detail Light (using Arc 66)
        page_light.goto(f"{BASE_URL}/arcs/66/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/05_arc_detail_light_after.png")
        print("  -> Captured: 05_arc_detail_light_after.png")

        # Habits Light
        page_light.goto(f"{BASE_URL}/habits/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_light_after.png")
        print("  -> Captured: 07_habits_light_after.png")

        # Analytics Light
        page_light.goto(f"{BASE_URL}/analytics/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/09_analytics_light_after.png")
        print("  -> Captured: 09_analytics_light_after.png")

        # Journal Light
        page_light.goto(f"{BASE_URL}/journal/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/08_journal_light_after.png")
        print("  -> Captured: 08_journal_light_after.png")

        # Profile Light
        page_light.goto(f"{BASE_URL}/accounts/profile/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_light.screenshot(path=f"{SCREENSHOT_DIR}/11_profile_after.png")
        print("  -> Captured: 11_profile_after.png")

        ctx_light.close()

        # =====================================================================
        # 2. Desktop Dark Context
        # =====================================================================
        print("Capturing Desktop Dark screens...")
        ctx_dark = browser.new_context(viewport={"width": 1440, "height": 900})
        ctx_dark.add_init_script("try { window.localStorage.setItem('winter_arc_theme', 'dark'); } catch(e){}")
        ctx_dark.add_cookies([session_cookie])
        page_dark = ctx_dark.new_page()
        page_dark.set_default_navigation_timeout(60000)

        # Dashboard Dark
        page_dark.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="domcontentloaded")
        time.sleep(0.8)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_dark_after.png")
        print("  -> Captured: 03_dashboard_dark_after.png")

        # Tasks Dark
        page_dark.goto(f"{BASE_URL}/tasks/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/06_tasks_dark_after.png")
        print("  -> Captured: 06_tasks_dark_after.png")

        # Habits Dark
        page_dark.goto(f"{BASE_URL}/habits/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_dark_after.png")
        print("  -> Captured: 07_habits_dark_after.png")

        # Analytics Dark
        page_dark.goto(f"{BASE_URL}/analytics/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/09_analytics_dark_after.png")
        print("  -> Captured: 09_analytics_dark_after.png")

        # Focus Mode
        page_dark.goto(f"{BASE_URL}/focus/", wait_until="domcontentloaded")
        time.sleep(1.0)
        page_dark.screenshot(path=f"{SCREENSHOT_DIR}/10_focus_after.png")
        print("  -> Captured: 10_focus_after.png")

        ctx_dark.close()

        # =====================================================================
        # 3. Mobile Context (iPhone 14/15 390x844)
        # =====================================================================
        print("Capturing Mobile screens...")
        ctx_mobile = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True
        )
        ctx_mobile.add_init_script("try { window.localStorage.setItem('winter_arc_theme', 'dark'); } catch(e){}")
        ctx_mobile.add_cookies([session_cookie])
        page_mob = ctx_mobile.new_page()
        page_mob.set_default_navigation_timeout(60000)

        # Mobile Landing
        page_mob.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
        time.sleep(0.8)
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/01_landing_mobile_after.png")
        print("  -> Captured: 01_landing_mobile_after.png")

        # Mobile Login
        page_mob.goto(f"{BASE_URL}/accounts/login/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/02_login_mobile_after.png")
        print("  -> Captured: 02_login_mobile_after.png")

        # Mobile Auth & Dashboard
        ctx_mobile.add_cookies([session_cookie])
        page_mob.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="domcontentloaded")
        page_mob.evaluate("window.WinterArcTheme ? window.WinterArcTheme.setTheme('dark') : document.documentElement.setAttribute('data-theme', 'dark'); localStorage.setItem('winter_arc_theme', 'dark');")
        time.sleep(0.8)
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/03_dashboard_mobile_after.png")
        print("  -> Captured: 03_dashboard_mobile_after.png")

        # Mobile Habits
        page_mob.goto(f"{BASE_URL}/habits/", wait_until="domcontentloaded")
        time.sleep(0.6)
        page_mob.screenshot(path=f"{SCREENSHOT_DIR}/07_habits_mobile_after.png")
        print("  -> Captured: 07_habits_mobile_after.png")

        ctx_mobile.close()
        browser.close()
        print("All cinematic 3D redesign screenshots captured successfully!")

finally:
    print("Terminating test server...")
    server_process.terminate()
    try:
        server_process.wait(timeout=5)
    except Exception:
        server_process.kill()
    try:
        server_log.close()
    except Exception:
        pass
