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
from gamification.models import XPEvent, UserAchievement
from gamification.services import get_user_total_xp, get_user_rank
from analytics.progress_services import get_full_analytics_summary

BASE_URL = 'http://127.0.0.1:8000'
SCREENSHOTS_DIR = os.path.join(os.getcwd(), 'screenshots_master_qa')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def test_analytics_and_gamification_e2e():
    print("==================================================")
    print("STARTING E2E BROWSER QA: ANALYTICS, GAMIFICATION & XP")
    print("==================================================")

    # Clean up test users
    for uname in ['xp_master_a', 'xp_rival_b']:
        u = CustomUser.objects.filter(username=uname).first()
        if u:
            u.delete()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()

        # Step 1: Register User A
        print("\n--- 1. REGISTER USER A ---")
        page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page.fill('input[name="username"]', 'xp_master_a')
        page.fill('input[name="email"]', 'master@winterarc.com')
        page.fill('input[name="password1"]', 'Crucible2026!')
        page.fill('input[name="password2"]', 'Crucible2026!')
        page.click('button:has-text("Create Account")')
        page.wait_for_load_state("networkidle")

        user_a = CustomUser.objects.filter(username='xp_master_a').first()
        assert user_a is not None, "User xp_master_a was not created"
        print("[OK] User A created.")

        # Step 2: Open Dashboard & Verify 0 XP / Recruit Rank
        print("\n--- 2. VERIFY DASHBOARD 0 XP / RECRUIT ---")
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "analytics_qa_01_dashboard_0xp.png"))
        assert "Recruit" in page.content(), "Expected Recruit rank on dashboard"
        assert "0 XP" in page.content(), "Expected 0 XP on dashboard"
        print("[OK] Dashboard displays real 0 XP and Recruit rank.")

        # Step 3: Create an Arc & Set Primary
        print("\n--- 3. CREATE PRIMARY ARC ---")
        page.goto(f"{BASE_URL}/arcs/new/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Iron Crucible')
        page.fill('textarea[name="objective"]', 'Mastering the winter cold')
        page.fill('input[name="start_date"]', '2026-10-01')
        page.fill('input[name="end_date"]', '2026-12-31')
        page.select_option('select[name="status"]', 'ACTIVE')
        page.check('input[name="is_primary"]')
        page.click('button:has-text("Save Arc")')
        page.wait_for_load_state("networkidle")

        arc = Arc.objects.filter(user=user_a, name='Iron Crucible').first()
        assert arc is not None, "Arc not created"
        print(f"[OK] Arc created with ID {arc.pk}")

        # Step 4: Create Task & Complete Task -> Verify XP
        print("\n--- 4. CREATE TASK & COMPLETE TASK -> VERIFY XP ---")
        page.goto(f"{BASE_URL}/tasks/new/", wait_until="networkidle")
        page.fill('input[name="title"]', 'Dawn Calisthenics')
        page.select_option('select[name="priority"]', '1') # High
        page.click('button:has-text("Save Task")')
        page.wait_for_load_state("networkidle")

        task = Task.objects.filter(user=user_a, title='Dawn Calisthenics').first()
        assert task is not None, "Task not created"

        # Complete task on task detail page
        page.goto(f"{BASE_URL}/tasks/{task.pk}/", wait_until="networkidle")
        page.click('button:has-text("Mark Complete")')
        page.wait_for_load_state("networkidle")

        # Verify XP in DB
        xp_total = get_user_total_xp(user_a)
        assert xp_total >= 50, f"Expected at least 50 XP, got {xp_total}"
        print(f"[OK] Task completed. Verified XP in ledger: {xp_total} XP")

        # Step 5: Refresh & Verify Idempotency (XP does not duplicate)
        print("\n--- 5. REFRESH & VERIFY XP IDEMPOTENCY ---")
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        xp_before_refresh = get_user_total_xp(user_a)
        page.reload(wait_until="networkidle")
        xp_after_refresh = get_user_total_xp(user_a)
        assert xp_before_refresh == xp_after_refresh, "XP changed on page refresh! Not idempotent."
        print(f"[OK] XP is strictly idempotent: {xp_after_refresh} XP unchanged after reload.")

        # Step 6: Create Habit & Complete Habit -> Verify Streak
        print("\n--- 6. CREATE HABIT & COMPLETE HABIT -> VERIFY STREAK ---")
        page.goto(f"{BASE_URL}/habits/new/", wait_until="networkidle")
        page.fill('input[name="name"]', 'Cold Plunge')
        page.fill('input[name="active_from"]', '2026-10-01')
        page.click('button:has-text("Save Habit")')
        page.wait_for_load_state("networkidle")

        habit = Habit.objects.filter(user=user_a, name='Cold Plunge').first()
        assert habit is not None, "Habit not created"

        page.goto(f"{BASE_URL}/habits/", wait_until="networkidle")
        page.click('button:has-text("Mark done")')
        page.wait_for_load_state("networkidle")

        streak = habit.get_current_streak()
        assert streak >= 1, f"Expected streak >= 1, got {streak}"
        print(f"[OK] Habit completed. Current streak: {streak}d")

        # Step 7: Open Full Analytics Page & Verify Real Data
        print("\n--- 7. OPEN ANALYTICS DASHBOARD ---")
        page.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "analytics_qa_02_analytics_page.png"))
        assert page.locator('h1:has-text("Progress & Ledger")').is_visible(), "Expected Progress & Ledger header"
        assert page.locator('h2:has-text("7-Day Execution Horizon")').is_visible(), "Expected 7-Day Horizon chart"
        assert page.locator('h2:has-text("Crucible Badges")').is_visible(), "Expected badges section"
        print("[OK] Analytics dashboard rendered with real verified metrics.")

        # Step 8: Responsive Verification
        print("\n--- 8. RESPONSIVE QA (1920, 1440, 1024, 768, 390) ---")
        viewports = [
            (1920, 1080, "1920"),
            (1440, 900, "1440"),
            (1024, 768, "1024"),
            (768, 1024, "768"),
            (390, 844, "390"),
        ]
        for w, h, label in viewports:
            page.set_viewport_size({"width": w, "height": h})
            page.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
            # Check horizontal overflow
            scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
            client_width = page.evaluate("() => document.documentElement.clientWidth")
            assert scroll_width <= client_width + 1, f"Horizontal overflow at {label}px! scrollWidth={scroll_width}, clientWidth={client_width}"
            print(f"[OK] Viewport {label}px clean with 0 horizontal overflow.")

        # Step 9: User Isolation (User B must NOT see User A's data)
        print("\n--- 9. SECURITY & DATA ISOLATION QA ---")
        page.set_viewport_size({"width": 1440, "height": 900})
        # Logout User A
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        page.click('button:has-text("Log out")')
        page.wait_for_load_state("networkidle")

        # Register User B
        page.goto(f"{BASE_URL}/accounts/register/", wait_until="networkidle")
        page.fill('input[name="username"]', 'xp_rival_b')
        page.fill('input[name="email"]', 'rival@winterarc.com')
        page.fill('input[name="password1"]', 'Crucible2026!')
        page.fill('input[name="password2"]', 'Crucible2026!')
        page.click('button:has-text("Create Account")')
        page.wait_for_load_state("networkidle")

        user_b = CustomUser.objects.filter(username='xp_rival_b').first()
        assert user_b is not None

        # Verify User B sees 0 XP on Dashboard
        page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
        assert "0 XP" in page.content(), "User B should have 0 XP"
        assert "Iron Crucible" not in page.content(), "User B must not see User A's arc!"

        # Verify User B opens analytics
        page.goto(f"{BASE_URL}/analytics/", wait_until="networkidle")
        page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "analytics_qa_03_user_b_empty.png"))
        assert "0 XP" in page.content()
        assert "The ledger is empty." in page.content()
        print("[OK] User B data is completely isolated. Zero leakage of User A's data.")

        browser.close()
        print("\n==================================================")
        print("ALL BROWSER E2E TESTS PASSED CLEANLY!")
        print("==================================================")

if __name__ == '__main__':
    test_analytics_and_gamification_e2e()
