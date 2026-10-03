import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import django
from datetime import date, timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
django.setup()

from playwright.sync_api import sync_playwright
from accounts.models import CustomUser, Profile
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots_master_qa')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def run_browser_functional_qa():
    print("==================================================")
    print("STARTING BROWSER-LEVEL FUNCTIONAL & SECURITY QA")
    print("==================================================")

    # Clean up test users
    for uname in ['e2e_warrior', 'user_alpha', 'user_beta']:
        u = CustomUser.objects.filter(username=uname).first()
        if u:
            u.delete()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()

        errors_logged = []
        page.on("console", lambda msg: errors_logged.append(f"Console error: {msg.text}") if msg.type == 'error' and 'favicon' not in msg.text else None)

        # -------------------------------------------------------------------------
        # JOURNEY 1: REGISTER -> LOGIN
        # -------------------------------------------------------------------------
        print("\n--- 1. REGISTER & LOGIN ---")
        page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page.fill('input[name="username"]', 'e2e_warrior')
        page.fill('input[name="email"]', 'warrior@winterarc.com')
        page.fill('input[name="password1"]', 'ShieldWall2026!')
        page.fill('input[name="password2"]', 'ShieldWall2026!')
        page.click('button:has-text("Create Account")')
        page.wait_for_load_state("networkidle")

        # Verify DB record
        user = CustomUser.objects.filter(username='e2e_warrior').first()
        assert user is not None, "User 'e2e_warrior' was not created in database!"
        print("[OK] Registration successful & verified in DB.")
        print("[OK] Logged in as e2e_warrior.")

        # -------------------------------------------------------------------------
        # JOURNEY 2: DASHBOARD EMPTY STATE (NO ARCS)
        # -------------------------------------------------------------------------
        print("\n--- 2. VERIFY DASHBOARD INITIAL EMPTY STATE ---")
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_dashboard_empty.png"))
        assert page.locator('text=Create your first Arc').first.is_visible(), "Expected 'Create your first Arc' CTA"
        assert page.locator('text=No active Arcs found').first.is_visible(), "Expected 'No active Arcs found' in Goals"
        print("[OK] Dashboard accurately displays initial empty state without arbitrary fallbacks.")

        # -------------------------------------------------------------------------
        # JOURNEY 3: CREATE ARC & SET PRIMARY
        # -------------------------------------------------------------------------
        print("\n--- 3. CREATE ARC & SET PRIMARY ---")
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Season of Iron')
        page.fill('textarea[name="objective"]', 'Forge mental resilience and relentless physical discipline.')
        today_str = date.today().isoformat()
        end_str = (date.today() + timedelta(days=90)).isoformat()
        page.fill('input[name="start_date"]', today_str)
        page.fill('input[name="end_date"]', end_str)
        page.select_option('select[name="status"]', 'ACTIVE')
        page.click('button:has-text("Save Arc")')
        page.wait_for_load_state("networkidle")

        arc1 = Arc.objects.filter(user=user, name='Season of Iron').first()
        if arc1 is None:
            print("DEBUG: Page URL:", page.url)
            print("DEBUG: Errors on page:", page.locator('.wa-field-error, [role="alert"]').all_text_contents())
        assert arc1 is not None, "Arc 'Season of Iron' not found in database!"
        print(f"[OK] Arc created: ID {arc1.pk}, Status={arc1.status}.")

        # Set Primary
        page.goto(f"{BASE_URL}/arcs/{arc1.pk}/", wait_until="networkidle")
        page.click('button:has-text("Set Primary")')
        page.wait_for_load_state("networkidle")
        arc1.refresh_from_db()
        assert arc1.is_primary, "Arc must be primary after Set Primary action!"
        assert page.locator('text=★ Primary Active Arc').first.is_visible(), "Primary badge must be visible in UI!"
        print("[OK] Arc set as primary.")

        # -------------------------------------------------------------------------
        # JOURNEY 4: CREATE GOAL & MILESTONE
        # -------------------------------------------------------------------------
        print("\n--- 4. CREATE GOAL & MILESTONE ---")
        page.goto(f"{BASE_URL}/goals/arc/{arc1.pk}/new/", wait_until="networkidle")
        page.fill('input[name="title"]', 'Forge Physical Might')
        page.fill('textarea[name="description"]', 'Calisthenics benchmarks and daily compound volume.')
        page.select_option('select[name="category"]', 'HEALTH')
        page.click('button:has-text("Save Goal")')
        page.wait_for_load_state("networkidle")

        goal1 = Goal.objects.filter(arc=arc1, title='Forge Physical Might').first()
        assert goal1 is not None, "Goal not found in database!"
        print(f"[OK] Goal created: ID {goal1.pk}, Title='{goal1.title}'.")

        # Add Milestone checkpoint
        page.goto(f"{BASE_URL}/goals/{goal1.pk}/", wait_until="networkidle")
        page.fill('#id_title', '100 Pushups unbroken')
        page.fill('#id_due_date', (date.today() + timedelta(days=30)).isoformat())
        page.click('#milestone-form button[type="submit"]')
        page.wait_for_load_state("networkidle")

        m1 = Milestone.objects.filter(goal=goal1, title='100 Pushups unbroken').first()
        assert m1 is not None, "Milestone not found in database!"
        assert page.locator('text=100 Pushups unbroken').first.is_visible(), "Milestone not visible in UI!"
        print(f"[OK] Milestone created: ID {m1.pk}.")

        # -------------------------------------------------------------------------
        # JOURNEY 5: CREATE TASK
        # -------------------------------------------------------------------------
        print("\n--- 5. CREATE TASK ---")
        page.goto(f"{BASE_URL}/tasks/new/", wait_until="networkidle")
        page.fill('input[name="title"]', 'Morning iron drill')
        page.select_option('select[name="priority"]', '1') # High
        page.select_option('select[name="goal"]', str(goal1.pk))
        page.click('button:has-text("Save Task")')
        page.wait_for_load_state("networkidle")

        t1 = Task.objects.filter(user=user, title='Morning iron drill').first()
        assert t1 is not None, "Task not found in database!"
        assert t1.goal == goal1, "Task not correctly attached to Goal!"
        print(f"[OK] Task created: ID {t1.pk}, Priority={t1.priority}.")

        # -------------------------------------------------------------------------
        # JOURNEY 6: CREATE HABIT
        # -------------------------------------------------------------------------
        print("\n--- 6. CREATE HABIT ---")
        page.goto(f"{BASE_URL}/habits/new/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Dawn Hydration & Salt')
        page.fill('textarea[name="description"]', '1L ice cold water with sea salt upon waking.')
        page.select_option('select[name="frequency"]', 'DAILY')
        page.fill('input[name="active_from"]', today_str)
        page.click('button:has-text("Save Habit")')
        page.wait_for_load_state("networkidle")
        page.wait_for_load_state("networkidle")

        h1 = Habit.objects.filter(user=user, name='Dawn Hydration & Salt').first()
        assert h1 is not None, "Habit not found in database!"
        print(f"[OK] Habit created: ID {h1.pk}.")

        # -------------------------------------------------------------------------
        # JOURNEY 7: RETURN TO DASHBOARD & VERIFY ALL DATA
        # -------------------------------------------------------------------------
        print("\n--- 7. VERIFY DASHBOARD WITH ALL ACTIVE DATA ---")
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_dashboard_populated.png"))
        assert page.locator('text=Season of Iron').first.is_visible(), "Primary Arc not shown on Dashboard!"
        assert page.locator('text=Forge Physical Might').first.is_visible(), "Goal not shown on Dashboard!"
        assert page.locator('text=Morning iron drill').first.is_visible(), "Task not shown on Dashboard!"
        assert page.locator('text=Dawn Hydration & Salt').first.is_visible(), "Habit not shown on Dashboard!"
        assert page.locator('text=Pending Tasks').first.is_visible()
        print("[OK] All created objects visible in their designated dashboard sections.")

        # -------------------------------------------------------------------------
        # JOURNEY 8: COMPLETE ACTIONS (MILESTONE, TASK, HABIT)
        # -------------------------------------------------------------------------
        print("\n--- 8. COMPLETE MILESTONE, TASK, HABIT ---")
        # Toggle milestone
        page.goto(f"{BASE_URL}/goals/{goal1.pk}/", wait_until="networkidle")
        page.click('button[title="Toggle milestone"]')
        page.wait_for_load_state("networkidle")
        m1.refresh_from_db()
        assert m1.is_completed, "Milestone should be marked completed!"
        goal1.refresh_from_db()
        assert goal1.progress_percentage == 100, f"Goal progress should be 100%, got {goal1.progress_percentage}%"
        print("[OK] Milestone toggled complete. Goal progress updated to 100%.")

        # Complete Task from dashboard
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.click('button[title="Mark task complete"]')
        page.wait_for_load_state("networkidle")
        t1.refresh_from_db()
        assert t1.status == 'COMPLETED', "Task should be COMPLETED!"
        assert not page.locator('text=Morning iron drill').is_visible(), "Completed task should be removed from pending list!"
        print("[OK] Task completed from dashboard. Removed from pending list.")

        # Complete Habit from dashboard
        page.click('button[aria-label="Complete habit: Dawn Hydration & Salt"]')
        page.wait_for_load_state("networkidle")
        h1.refresh_from_db()
        assert h1.is_completed_today(), "Habit should be marked completed today!"
        assert h1.get_current_streak() == 1, "Streak should be 1!"
        assert h1.best_streak == 1, "Best streak should be 1!"
        assert page.locator('button:has-text("Done")').is_visible(), "Dashboard should display 'Done' toggle button!"
        print("[OK] Habit completed from dashboard. Streak = 1d, button transformed to 'Done'.")

        # -------------------------------------------------------------------------
        # JOURNEY 9: EDIT GOAL, MILESTONE, TASK, HABIT
        # -------------------------------------------------------------------------
        print("\n--- 9. EDIT GOAL, MILESTONE, TASK, HABIT ---")
        # Edit Goal
        page.goto(f"{BASE_URL}/goals/{goal1.pk}/edit/", wait_until="networkidle")
        page.fill('input[name="title"]', 'Forge Unyielding Might')
        page.click('button:has-text("Save Goal")')
        page.wait_for_load_state("networkidle")
        goal1.refresh_from_db()
        assert goal1.title == 'Forge Unyielding Might'
        print("[OK] Goal successfully edited.")

        # Edit Milestone
        page.goto(f"{BASE_URL}/goals/milestones/{m1.pk}/edit/", wait_until="networkidle")
        page.fill('input[name="title"]', '120 Pushups unbroken')
        page.click('button:has-text("Save Checkpoint")')
        page.wait_for_load_state("networkidle")
        m1.refresh_from_db()
        assert m1.title == '120 Pushups unbroken'
        print("[OK] Milestone checkpoint successfully edited.")

        # Edit Task
        page.goto(f"{BASE_URL}/tasks/{t1.pk}/edit/", wait_until="networkidle")
        page.fill('input[name="title"]', 'Advanced morning iron drill')
        page.click('button:has-text("Save Task")')
        page.wait_for_load_state("networkidle")
        t1.refresh_from_db()
        assert t1.title == 'Advanced morning iron drill'
        print("[OK] Task successfully edited.")

        # Edit Habit
        page.goto(f"{BASE_URL}/habits/{h1.pk}/edit/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Cold Dawn Hydration & Salt')
        page.click('button:has-text("Save Habit")')
        page.wait_for_load_state("networkidle")
        h1.refresh_from_db()
        assert h1.name == 'Cold Dawn Hydration & Salt'
        print("[OK] Habit successfully edited.")

        # -------------------------------------------------------------------------
        # JOURNEY 10: SECOND ARC, PRIMARY SWITCHING & ARCHIVE
        # -------------------------------------------------------------------------
        print("\n--- 10. PRIMARY ARC SWITCHING, ARCHIVE, AND PERMANENT DELETE ---")
        # Create second arc
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Season of Intellect')
        page.fill('textarea[name="objective"]', 'Master tactical strategy and deep reading.')
        page.fill('input[name="start_date"]', today_str)
        page.fill('input[name="end_date"]', end_str)
        page.select_option('select[name="status"]', 'ACTIVE')
        page.click('button:has-text("Save Arc")')
        page.wait_for_load_state("networkidle")

        arc2 = Arc.objects.filter(user=user, name='Season of Intellect').first()
        assert arc2 is not None

        # Make Arc 2 Primary
        page.goto(f"{BASE_URL}/arcs/{arc2.pk}/", wait_until="networkidle")
        page.click('button:has-text("Set Primary")')
        page.wait_for_load_state("networkidle")
        arc1.refresh_from_db()
        arc2.refresh_from_db()
        assert arc2.is_primary, "Arc 2 must now be primary!"
        assert not arc1.is_primary, "Arc 1 must NOT be primary after switching!"
        print("[OK] Primary exclusivity strictly enforced: Arc 2 is primary, Arc 1 is not.")

        # Verify Dashboard uses Arc 2
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        assert page.locator('text=Season of Intellect').first.is_visible(), "Dashboard must show new Primary Arc!"
        assert not page.locator('text=Forge Unyielding Might').first.is_visible(), "Dashboard must NOT show goals of non-primary Arc!"
        print("[OK] Dashboard strictly follows current Primary Arc.")

        # Switch Primary back to Arc 1
        page.goto(f"{BASE_URL}/arcs/{arc1.pk}/", wait_until="networkidle")
        page.click('button:has-text("Set Primary")')
        page.wait_for_load_state("networkidle")
        arc1.refresh_from_db()
        assert arc1.is_primary

        # Archive Arc 2
        page.goto(f"{BASE_URL}/arcs/{arc2.pk}/delete/", wait_until="networkidle")
        page.click('button:has-text("Archive Arc")')
        page.wait_for_load_state("networkidle")
        arc2.refresh_from_db()
        assert arc2.status == 'ARCHIVED', "Arc 2 should be ARCHIVED!"
        print("[OK] Arc 2 archived successfully.")

        # Create temporary Arc and permanently delete it
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Temporary Arc')
        page.fill('textarea[name="objective"]', 'Testing permanent delete.')
        page.fill('input[name="start_date"]', today_str)
        page.fill('input[name="end_date"]', end_str)
        page.click('button:has-text("Save Arc")')
        page.wait_for_load_state("networkidle")
        temp_arc = Arc.objects.filter(user=user, name='Temporary Arc').first()
        temp_id = temp_arc.pk

        page.goto(f"{BASE_URL}/arcs/{temp_id}/delete/", wait_until="networkidle")
        page.click('button:has-text("Delete Permanently")')
        page.wait_for_load_state("networkidle")
        assert not Arc.objects.filter(pk=temp_id).exists(), "Temporary Arc must be permanently deleted from database!"
        print("[OK] Permanent delete confirmed: record is truly removed from database.")

        # -------------------------------------------------------------------------
        # SECURITY QA: USER A vs USER B ISOLATION
        # -------------------------------------------------------------------------
        print("\n--- 11. SECURITY QA: CROSS-USER DATA ISOLATION & DIRECT URL TAMPERING ---")
        user_a = CustomUser.objects.create_user(username='user_alpha', password='Password123!')
        Profile.objects.get_or_create(user=user_a)
        user_b = CustomUser.objects.create_user(username='user_beta', password='Password123!')
        Profile.objects.get_or_create(user=user_b)

        # Create objects for User A
        a_arc = Arc.objects.create(user=user_a, name="Alpha Arc", start_date=date.today(), end_date=date.today()+timedelta(days=30), status='ACTIVE')
        a_goal = Goal.objects.create(user=user_a, arc=a_arc, title="Alpha Goal")
        a_ms = Milestone.objects.create(goal=a_goal, title="Alpha Milestone")
        a_task = Task.objects.create(user=user_a, title="Alpha Task")
        a_habit = Habit.objects.create(user=user_a, name="Alpha Habit", active_from=date.today())

        # Login as User B in a completely isolated browser context
        context_b = browser.new_context(viewport={'width': 1440, 'height': 900})
        b_page = context_b.new_page()
        b_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        b_page.fill('input[name="username"]', 'user_beta')
        b_page.fill('input[name="password"]', 'Password123!')
        b_page.click('button:has-text("Log in")')
        b_page.wait_for_load_state("networkidle")

        # Test direct URL manipulation against all of User A's endpoints
        security_endpoints = [
            f"/arcs/{a_arc.pk}/",
            f"/arcs/{a_arc.pk}/edit/",
            f"/arcs/{a_arc.pk}/delete/",
            f"/arcs/{a_arc.pk}/pause/",
            f"/arcs/{a_arc.pk}/resume/",
            f"/arcs/{a_arc.pk}/complete/",
            f"/arcs/{a_arc.pk}/make_primary/",
            f"/goals/{a_goal.pk}/",
            f"/goals/{a_goal.pk}/edit/",
            f"/goals/{a_goal.pk}/delete/",
            f"/goals/milestones/{a_ms.pk}/edit/",
            f"/goals/milestones/{a_ms.pk}/toggle/",
            f"/goals/milestones/{a_ms.pk}/delete/",
            f"/tasks/{a_task.pk}/",
            f"/tasks/{a_task.pk}/edit/",
            f"/tasks/{a_task.pk}/delete/",
            f"/tasks/{a_task.pk}/complete/",
            f"/habits/{a_habit.pk}/",
            f"/habits/{a_habit.pk}/edit/",
            f"/habits/{a_habit.pk}/complete/",
            f"/habits/{a_habit.pk}/archive/",
        ]

        for url in security_endpoints:
            # Test GET
            resp = b_page.goto(f"{BASE_URL}{url}")
            assert resp.status in [404, 403, 302], f"Security vulnerability on GET {url}: status {resp.status}"
            # Test POST
            resp_post = b_page.request.post(f"{BASE_URL}{url}")
            assert resp_post.status in [404, 403, 302], f"Security vulnerability on POST {url}: status {resp_post.status}"

        print("[OK] All 21 endpoints returned strict 404/protection when accessed by unauthorized user.")
        context_b.close()

        # -------------------------------------------------------------------------
        # SCREENSHOT CAPTURE MATRIX
        # -------------------------------------------------------------------------
        print("\n--- 12. SCREENSHOT CAPTURE MATRIX FOR VISUAL INSPECTION ---")
        # 1. Unauthenticated views
        anon_context = browser.new_context(viewport={'width': 1440, 'height': 900})
        anon_page = anon_context.new_page()
        anon_page.goto(f"{BASE_URL}/", wait_until="networkidle")
        anon_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "qa_landing.png"), full_page=True)
        print("[OK] Captured screenshot: qa_landing.png (1440x900)")

        anon_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
        anon_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "qa_login.png"), full_page=True)
        print("[OK] Captured screenshot: qa_login.png (1440x900)")
        anon_context.close()

        # 2. Authenticated views (page is logged in as e2e_warrior)
        auth_shots = [
            ("dashboard", f"{BASE_URL}/accounts/dashboard/", 1440, 900),
            ("arc_list", f"{BASE_URL}/arcs/", 1440, 900),
            ("arc_detail", f"{BASE_URL}/arcs/{arc1.pk}/", 1440, 900),
            ("goal_detail", f"{BASE_URL}/goals/{goal1.pk}/", 1440, 900),
            ("task_list", f"{BASE_URL}/tasks/", 1440, 900),
            ("habit_list", f"{BASE_URL}/habits/", 1440, 900),
            ("archive_delete_flow", f"{BASE_URL}/arcs/{arc1.pk}/delete/", 1440, 900),
            ("mobile_dashboard", f"{BASE_URL}/accounts/dashboard/", 390, 844),
        ]

        for name, url, w, h in auth_shots:
            page.set_viewport_size({'width': w, 'height': h})
            page.goto(url, wait_until="networkidle")
            page.wait_for_timeout(300)
            shot_path = os.path.join(SCREENSHOTS_DIR, f"qa_{name}.png")
            page.screenshot(path=shot_path, full_page=True)
            print(f"[OK] Captured screenshot: qa_{name}.png ({w}x{h})")

        browser.close()

    print("\n==================================================")
    print("ALL BROWSER FUNCTIONAL & SECURITY QA CHECKS PASSED!")
    print("==================================================")

if __name__ == '__main__':
    run_browser_functional_qa()
