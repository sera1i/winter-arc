import os
import sys
import time
import subprocess
import urllib.request
import json
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', line_buffering=True)

BASE_URL = 'http://127.0.0.1:8000'

VIEWPORTS = [320, 360, 375, 390, 414, 430]

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

def audit():
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # Get fixture IDs
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
    django.setup()
    from django.contrib.auth import get_user_model
    from arcs.models import Arc
    from goals.models import Goal
    from tasks.models import Task
    from habits.models import Habit
    from journal.models import JournalEntry

    User = get_user_model()
    u = User.objects.get(username='browseruser1')
    arc = Arc.objects.filter(user=u).first()
    goal = Goal.objects.filter(user=u).first()
    task = Task.objects.filter(user=u).first()
    habit = Habit.objects.filter(user=u).first()
    journal = JournalEntry.objects.filter(user=u).first()

    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        wait_for_server(f"{BASE_URL}/accounts/login/", timeout=30)

    routes = [
        # Authenticated
        ("/accounts/dashboard/", "Dashboard", True),
        ("/arcs/", "Arcs List", True),
        ("/arcs/new/", "Arc Create", True),
        (f"/arcs/{arc.pk}/" if arc else "/arcs/", "Arc Detail", True),
        (f"/arcs/{arc.pk}/edit/" if arc else "/arcs/", "Arc Edit", True),
        ("/tasks/", "Tasks List", True),
        ("/tasks/new/", "Task Create", True),
        (f"/tasks/{task.pk}/" if task else "/tasks/", "Task Detail", True),
        ("/habits/", "Habits List", True),
        ("/habits/new/", "Habit Create", True),
        (f"/habits/{habit.pk}/" if habit else "/habits/", "Habit Detail", True),
        (f"/goals/{goal.pk}/" if goal else "/accounts/dashboard/", "Goal Detail", True),
        ("/journal/", "Journal List", True),
        ("/journal/new/", "Journal Create", True),
        ("/notifications/", "Notifications List", True),
        ("/notifications/preferences/", "Notification Preferences", True),
        ("/analytics/", "Analytics", True),
        ("/accounts/profile/", "Profile", True),
        # Public
        ("/", "Landing Page", False),
        ("/accounts/login/", "Login Page", False),
        ("/accounts/register/", "Register Page", False),
        ("/winter-arc/", "SEO Pillar", False),
    ]

    overflow_finder_script = """() => {
        const docW = document.documentElement.clientWidth;
        const scrollW = document.documentElement.scrollWidth;
        const offenders = [];

        const all = document.querySelectorAll('*');
        for (const el of all) {
            // Ignore script, style, head, meta
            if (['SCRIPT', 'STYLE', 'HEAD', 'META', 'LINK', 'TITLE'].includes(el.tagName)) continue;
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') continue;

            // If the element is contained within an ancestor with overflow-x: auto or overflow-x: scroll,
            // that container intentionally manages horizontal scrolling.
            let isInsideScrollContainer = false;
            let parent = el.parentElement;
            while (parent && parent !== document.body && parent !== document.documentElement) {
                const parentStyle = window.getComputedStyle(parent);
                if (['auto', 'scroll'].includes(parentStyle.overflowX)) {
                    isInsideScrollContainer = true;
                    break;
                }
                parent = parent.parentElement;
            }
            if (isInsideScrollContainer) continue;

            // Check if element extends beyond viewport right edge
            if (rect.right > docW + 1) { // 1px threshold for rounding
                // Filter to leaf-most offending elements or significant containers
                offenders.push({
                    tag: el.tagName.toLowerCase(),
                    id: el.id,
                    className: (el.className && typeof el.className === 'string') ? el.className.split(' ').slice(0, 5).join(' ') : '',
                    right: Math.round(rect.right),
                    width: Math.round(rect.width),
                    overflowAmount: Math.round(rect.right - docW),
                    textSnippet: (el.innerText || '').substring(0, 40).replace(/\\n/g, ' ')
                });
            }
        }

        return {
            clientWidth: docW,
            scrollWidth: scrollW,
            hasOverflow: (scrollW > docW) || (offenders.length > 0),
            diff: Math.max(scrollW - docW, offenders.length > 0 ? offenders[0].overflowAmount : 0),
            offendersCount: offenders.length,
            offenders: offenders.slice(0, 10)
        };
    }"""

    results = {}

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            
            # First create authenticated context
            auth_context = browser.new_context(viewport={'width': 390, 'height': 844})
            auth_page = auth_context.new_page()
            auth_page.goto(f"{BASE_URL}/accounts/login/", wait_until="load")
            auth_page.fill('input[name="username"]', 'browseruser1')
            auth_page.fill('input[name="password"]', 'Password123!')
            with auth_page.expect_navigation(wait_until="load"):
                auth_page.click('#login-submit-btn')
            auth_page.close()

            # Now test viewports
            for vp_width in VIEWPORTS:
                print(f"\n==========================================")
                print(f"TESTING VIEWPORT WIDTH: {vp_width}px")
                print(f"==========================================")
                results[vp_width] = {}

                for path, name, is_auth in routes:
                    ctx = auth_context if is_auth else browser.new_context(viewport={'width': vp_width, 'height': 700})
                    page = ctx.new_page()
                    page.set_viewport_size({'width': vp_width, 'height': 700})
                    
                    try:
                        page.goto(f"{BASE_URL}{path}", wait_until="load")
                        page.wait_for_timeout(500) # allow any layout calculation
                        
                        diag = page.evaluate(overflow_finder_script)
                        results[vp_width][name] = diag

                        if diag['hasOverflow']:
                            print(f"  ❌ [{name}] ({path}): scrollWidth={diag['scrollWidth']} > clientWidth={diag['clientWidth']} (OVERFLOW by {diag['diff']}px)")
                            for off in diag['offenders'][:3]:
                                print(f"      -> <{off['tag']} class='{off['className']}'> width={off['width']}px, right={off['right']}px (+{off['overflowAmount']}px) '{off['textSnippet']}'")
                        else:
                            print(f"  ✓ [{name}] ({path}): OK (clientWidth={diag['clientWidth']}, scrollWidth={diag['scrollWidth']})")
                    except Exception as e:
                        print(f"  ⚠️ [{name}] ({path}): Error: {e}")
                    finally:
                        page.close()
                        if not is_auth:
                            ctx.close()

            browser.close()
    finally:
        if server_process:
            server_process.kill()

    with open('mobile_overflow_audit.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nAudit complete! Results saved to mobile_overflow_audit.json")

if __name__ == "__main__":
    audit()
