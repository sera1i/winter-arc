import os
import sys
import time
import subprocess
import urllib.request
from datetime import date
from playwright.sync_api import sync_playwright

SERVER_PORT = "8062"
BASE_URL = f"http://127.0.0.1:{SERVER_PORT}"
PYTHON_BIN = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/scratch/venv/bin/python"
SCREENSHOT_DIR = "/home/sera1i/.gemini/antigravity/brain/8af3ff42-f485-4dda-af86-85b192bffba3/screenshots/realtime_sync"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# 1. Setup test user and data in Django DB
setup_script = """
import os
from datetime import date
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'winter_arc.settings')
django.setup()
from django.contrib.auth import get_user_model
from arcs.models import Arc
from goals.models import Goal, Milestone
from tasks.models import Task
from habits.models import Habit, HabitCompletion
from gamification.models import XPEvent, Achievement, UserAchievement
from gamification.services import _ensure_achievements_seeded

User = get_user_model()
User.objects.filter(username='sync_browser_tester').delete()

user = User.objects.create_user(username='sync_browser_tester', password='crucible_pass_123')
_ensure_achievements_seeded()
first_task_ach = Achievement.objects.filter(code='FIRST_TASK').first()
if first_task_ach:
    UserAchievement.objects.create(user=user, achievement=first_task_ach)

arc = Arc.objects.create(
    user=user,
    name='Titan Crucible',
    objective='Total mastery',
    start_date=date(2026, 10, 1),
    end_date=date(2026, 12, 31),
    status='ACTIVE'
)

goal = Goal.objects.create(
    user=user,
    arc=arc,
    title='Forge Resilience',
    category='DISCIPLINE',
    target_value=10,
    unit='reps',
    status='IN_PROGRESS'
)

milestone = Milestone.objects.create(
    goal=goal,
    title='Milestone Alpha',
    due_date=date(2026, 11, 15)
)

t1 = Task.objects.create(
    user=user,
    goal=goal,
    title='Morning Heavy Ruck',
    priority=1,
    status='PENDING'
)

t2 = Task.objects.create(
    user=user,
    goal=goal,
    title='Evening Cold Plunge',
    priority=2,
    status='PENDING'
)

h1 = Habit.objects.create(
    user=user,
    name='Dawn Meditation',
    frequency='DAILY',
    active_from=date(2026, 10, 1)
)

print('USER_SETUP_COMPLETE')
"""

cmd = [PYTHON_BIN, "-c", setup_script]
res = subprocess.run(cmd, capture_output=True, text=True, cwd="/mnt/c/Users/seral/OneDrive/Desktop/winter_arc")
if "USER_SETUP_COMPLETE" not in res.stdout:
    print("Failed to setup user:", res.stdout, res.stderr)
    sys.exit(1)
print("Django test user and data seeded successfully.")

# 2. Launch server
server_process = subprocess.Popen(
    [PYTHON_BIN, "manage.py", "runserver", f"127.0.0.1:{SERVER_PORT}", "--noreload"],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

ready = False
for _ in range(40):
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=1) as resp:
            if resp.status in (200, 302):
                ready = True
                break
    except Exception:
        time.sleep(0.5)

if not ready:
    print("Server failed to start")
    if server_process:
        server_process.kill()
    sys.exit(1)

print(f"Server is live at {BASE_URL}")

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

        # Step A: Log in
        print("Logging in...")
        page.goto(f"{BASE_URL}/accounts/login/")
        page.fill("input[name='username']", "sync_browser_tester")
        page.fill("input[name='password']", "crucible_pass_123")
        page.click("#login-submit-btn")
        page.wait_for_url("**/dashboard/")

        print("Dashboard loaded successfully.")
        page.screenshot(path=f"{SCREENSHOT_DIR}/01_dashboard_initial.png", full_page=True)

        # Inspect initial values
        initial_xp = page.locator('[data-sync="total-xp"]').first.inner_text().strip()
        initial_tasks_today = page.locator('[data-sync="tasks-today-completed"]').first.inner_text().strip()
        initial_habits_ratio = page.locator('[data-sync="habits-today-ratio"]').first.inner_text().strip()
        print(f"Initial XP: '{initial_xp}' | Tasks Done: '{initial_tasks_today}' | Habits Ratio: '{initial_habits_ratio}'")
        assert "0 XP" in initial_xp, f"Expected initial XP 0 XP, got {initial_xp}"
        assert initial_tasks_today == "0", f"Expected tasks done 0, got {initial_tasks_today}"
        assert "0" in initial_habits_ratio, f"Expected habits done 0, got {initial_habits_ratio}"

        # Step B: Complete Task 1 via AJAX
        print("\n--- Testing Task Completion ---")
        task_row = page.locator("li.task-row:has-text('Morning Heavy Ruck')").first
        complete_btn = task_row.locator("button.wa-checkbox-btn").first
        
        # Click complete button
        complete_btn.click()
        
        # Wait for data-sync to update without reload
        page.wait_for_function("document.querySelector('[data-sync=\"total-xp\"]').innerText.includes('50')")
        page.wait_for_function("document.querySelector('[data-sync=\"tasks-today-completed\"]').innerText.trim() === '1'")

        # Verify UI state
        updated_xp = page.locator('[data-sync="total-xp"]').first.inner_text().strip()
        updated_tasks = page.locator('[data-sync="tasks-today-completed"]').first.inner_text().strip()
        print(f"After Task Complete -> Live XP: '{updated_xp}', Tasks Done: '{updated_tasks}'")
        assert "50 XP" in updated_xp, f"Expected 50 XP, got {updated_xp}"
        assert updated_tasks == "1", f"Expected 1 task completed, got {updated_tasks}"

        # Check line-through or strikethrough styling applied live
        title_el = task_row.locator("a:has-text('Morning Heavy Ruck'), [class*='line-through']").first
        classes = title_el.get_attribute("class") or ""
        print(f"Task title classes: {classes}")
        assert "line-through" in classes or "text-steel" in classes or "opacity-50" in classes

        page.screenshot(path=f"{SCREENSHOT_DIR}/02_task_completed_live.png", full_page=True)

        # Step C: Undo Task 1 via AJAX
        print("\n--- Testing Task Undo ---")
        undo_btn = task_row.locator("button.wa-checkbox-btn").first
        undo_btn.click()

        # Wait for data-sync to rollback without reload
        page.wait_for_function("document.querySelector('[data-sync=\"total-xp\"]').innerText.includes('0 XP')")
        page.wait_for_function("document.querySelector('[data-sync=\"tasks-today-completed\"]').innerText.trim() === '0'")

        undo_xp = page.locator('[data-sync="total-xp"]').first.inner_text().strip()
        undo_tasks = page.locator('[data-sync="tasks-today-completed"]').first.inner_text().strip()
        print(f"After Task Undo -> Live XP: '{undo_xp}', Tasks Done: '{undo_tasks}'")
        assert "0 XP" in undo_xp, f"Expected 0 XP after undo, got {undo_xp}"
        assert undo_tasks == "0", f"Expected 0 tasks done after undo, got {undo_tasks}"

        page.screenshot(path=f"{SCREENSHOT_DIR}/03_task_undone_live.png", full_page=True)

        # Step D: Complete Habit via AJAX
        print("\n--- Testing Habit Check-in ---")
        habit_row = page.locator("li:has-text('Dawn Meditation')").first
        habit_btn = habit_row.locator("button.wa-habit-btn").first
        habit_btn.click()

        page.wait_for_function("document.querySelector('[data-sync=\"total-xp\"]').innerText.includes('30 XP')")
        page.wait_for_function("document.querySelector('[data-sync=\"habits-today-ratio\"]').innerText.includes('1')")

        habit_xp = page.locator('[data-sync="total-xp"]').first.inner_text().strip()
        habit_ratio = page.locator('[data-sync="habits-today-ratio"]').first.inner_text().strip()
        print(f"After Habit Check-in -> Live XP: '{habit_xp}', Habits Ratio: '{habit_ratio}'")
        assert "30 XP" in habit_xp, f"Expected 30 XP, got {habit_xp}"
        assert "1" in habit_ratio, f"Expected 1 habit done, got {habit_ratio}"

        page.screenshot(path=f"{SCREENSHOT_DIR}/04_habit_completed_live.png", full_page=True)

        # Step E: Undo Habit Check-in via AJAX
        print("\n--- Testing Habit Undo ---")
        habit_undo_btn = habit_row.locator("button.wa-habit-btn").first
        habit_undo_btn.click()

        page.wait_for_function("document.querySelector('[data-sync=\"total-xp\"]').innerText.includes('0 XP')")
        page.wait_for_function("document.querySelector('[data-sync=\"habits-today-ratio\"]').innerText.includes('0')")

        habit_undo_xp = page.locator('[data-sync="total-xp"]').first.inner_text().strip()
        habit_undo_ratio = page.locator('[data-sync="habits-today-ratio"]').first.inner_text().strip()
        print(f"After Habit Undo -> Live XP: '{habit_undo_xp}', Habits Ratio: '{habit_undo_ratio}'")
        assert "0 XP" in habit_undo_xp, f"Expected 0 XP after undo, got {habit_undo_xp}"
        assert "0" in habit_undo_ratio, f"Expected 0 habits done after undo, got {habit_undo_ratio}"

        page.screenshot(path=f"{SCREENSHOT_DIR}/05_habit_undone_live.png", full_page=True)

        print("\nALL BROWSER REAL-TIME SYNC TESTS PASSED PERFECTLY!")

finally:
    if server_process:
        server_process.terminate()
        server_process.kill()
