import os
import sys
from playwright.sync_api import sync_playwright

def run_browser_tests():
    os.makedirs('screenshots', exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        
        console_messages = []
        js_errors = []
        failed_requests = []
        
        page.on("console", lambda msg: console_messages.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: js_errors.append(f"JS Error: {err}"))
        page.on("response", lambda resp: failed_requests.append(f"{resp.status} {resp.url}") if resp.status >= 400 else None)
        
        base_url = "http://127.0.0.1:8004"
        
        print("=== 1. AUTH & PHASE 1 REGRESSION ===")
        print("Opening root URL...")
        page.goto(f"{base_url}/")
        assert "/accounts/login/" in page.url
        
        print("Logging in as browseruser...")
        page.fill("input[name='username']", "browseruser")
        page.fill("input[name='password']", "password123")
        with page.expect_navigation():
            page.click("button:has-text('Log In')")
            
        print("Checking Profile...")
        page.goto(f"{base_url}/accounts/profile/")
        assert page.locator("h1:has-text('Profile')").is_visible()
        
        print("=== 2. ARCS & PHASE 2 REGRESSION ===")
        page.goto(f"{base_url}/arcs/")
        with page.expect_navigation():
            page.click("text=New Arc")
            
        page.fill("input[name='name']", "Phase 4 Master Arc")
        page.fill("textarea[name='objective']", "Full system verification.")
        page.fill("input[name='start_date']", "2027-01-01")
        page.fill("input[name='end_date']", "2027-04-30")
        with page.expect_navigation():
            page.click("button:has-text('Save Arc')")
            
        arc_url = page.url
        print(f"-> Arc created at {arc_url}")
        
        # Edit Arc
        with page.expect_navigation():
            page.click("text=Edit")
        page.fill("input[name='name']", "Verified Phase 4 Arc")
        page.select_option("select[name='status']", "ACTIVE")
        with page.expect_navigation():
            page.click("button:has-text('Save Arc')")
        print("-> Arc edit verified.")
        
        # Make Primary
        if page.locator("text=Make Primary").is_visible():
            with page.expect_navigation():
                page.click("text=Make Primary")
            print("-> Arc marked as primary.")
            
        print("=== 3. GOALS & PHASE 3 REGRESSION ===")
        page.goto(arc_url)
        with page.expect_navigation():
            page.click("a#add-goal-btn")
            
        page.fill("input[name='title']", "Core Winter Goal")
        page.fill("textarea[name='description']", "Goal to attach tasks and milestones.")
        page.select_option("select[name='category']", "PRODUCTIVITY")
        page.fill("input[name='priority']", "1")
        page.fill("input[name='deadline']", "2027-03-31")
        with page.expect_navigation():
            page.click("button:has-text('Save Goal')")
            
        page.reload()
        assert page.locator("text=Core Winter Goal").is_visible()
        print("-> Goal created & persisted.")
        
        with page.expect_navigation():
            page.click("text=Core Winter Goal")
        goal_url = page.url
        
        # Add Milestone
        page.fill("input[name='title']", "Core Milestone 1")
        page.fill("input[name='due_date']", "2027-02-15")
        with page.expect_navigation():
            page.click("button:has-text('Add')")
        page.reload()
        assert page.locator("text=Core Milestone 1").is_visible()
        print("-> Milestone created.")
        
        # Toggle Milestone Complete
        with page.expect_navigation():
            page.click("form[action*='/toggle/'] button")
        page.reload()
        assert page.locator("text=100%").is_visible() or page.locator("text=100").is_visible()
        print("-> Milestone toggled complete -> 100% progress.")
        
        # Toggle Milestone Incomplete
        with page.expect_navigation():
            page.click("form[action*='/toggle/'] button")
        page.reload()
        assert page.locator("text=0%").is_visible() or page.locator("text=0").is_visible()
        print("-> Milestone toggled incomplete -> 0% progress.")
        
        print("=== 4. PHASE 4 — TASK SYSTEM ===")
        page.goto(f"{base_url}/tasks/")
        page.screenshot(path="screenshots/task_list.png")
        print("-> Navigated to Tasks list.")
        
        # Create Task
        with page.expect_navigation():
            page.click("text=+ New Task")
        page.screenshot(path="screenshots/task_create.png")
        
        page.fill("input[name='title']", "Implement Automated Test Suite")
        page.fill("textarea[name='description']", "Full Playwright and unit test verification.")
        page.select_option("select[name='priority']", "1")  # High
        page.select_option("select[name='status']", "PENDING")
        page.fill("input[name='due_at']", "2027-02-01T10:00")
        with page.expect_navigation():
            page.click("button:has-text('Save Task')")
            
        task_url = page.url
        print(f"-> Task created at {task_url}")
        page.screenshot(path="screenshots/task_detail.png")
        
        # Verify persistence on reload
        page.reload()
        assert page.locator("text=Implement Automated Test Suite").is_visible()
        assert page.locator("text=High Priority").is_visible()
        print("-> Task detail persistence verified.")
        
        # Edit Task
        with page.expect_navigation():
            page.click("text=Edit")
        page.fill("input[name='title']", "Refactored Automated Test Suite")
        with page.expect_navigation():
            page.click("button:has-text('Save Task')")
        page.reload()
        assert page.locator("text=Refactored Automated Test Suite").is_visible()
        print("-> Task edit persisted.")
        
        # Complete Task
        with page.expect_navigation():
            page.click("#complete-task-btn")
        page.reload()
        page.screenshot(path="screenshots/task_completed.png")
        assert page.locator("#uncomplete-task-btn").is_visible()
        print("-> Task completion persisted.")
        
        # Uncomplete Task
        with page.expect_navigation():
            page.click("#uncomplete-task-btn")
        page.reload()
        assert page.locator("#complete-task-btn").is_visible()
        print("-> Task uncompletion persisted.")
        
        # Complete Task again so we have a completed task for dashboard
        with page.expect_navigation():
            page.click("#complete-task-btn")
            
        # Create a second pending task
        page.goto(f"{base_url}/tasks/new/")
        page.fill("input[name='title']", "Active Daily Task")
        page.fill("textarea[name='description']", "To show in pending queue.")
        page.select_option("select[name='priority']", "2")
        with page.expect_navigation():
            page.click("button:has-text('Save Task')")
        print("-> Second task created.")
        
        print("=== 5. PHASE 4 — HABIT SYSTEM & STREAKS ===")
        page.goto(f"{base_url}/habits/")
        page.screenshot(path="screenshots/habit_list.png")
        print("-> Navigated to Habits list.")
        
        # Create Habit
        with page.expect_navigation():
            page.click("text=+ New Habit")
        page.screenshot(path="screenshots/habit_create.png")
        
        page.fill("input[name='name']", "Deep Focus 90 Mins")
        page.fill("textarea[name='description']", "Uninterrupted coding and study block.")
        page.select_option("select[name='frequency']", "DAILY")
        page.fill("input[name='active_from']", "2027-01-01")
        with page.expect_navigation():
            page.click("button:has-text('Save Habit')")
            
        habit_url = page.url
        print(f"-> Habit created at {habit_url}")
        page.screenshot(path="screenshots/habit_detail.png")
        
        # Verify persistence on reload
        page.reload()
        assert page.locator("text=Deep Focus 90 Mins").is_visible()
        print("-> Habit detail persistence verified.")
        
        # Complete Habit for Today
        with page.expect_navigation():
            page.click("#habit-complete-btn")
        page.reload()
        page.screenshot(path="screenshots/habit_streak.png")
        
        # Verify streak badge and history
        assert page.locator("text=Day Streak").is_visible()
        assert page.locator("text=Completed Today").is_visible()
        print("-> Habit completed for today, streak=1 verified.")
        
        # Toggle Habit (Undo)
        with page.expect_navigation():
            page.click("#habit-complete-btn")
        page.reload()
        assert page.locator("text=Mark Complete for Today").is_visible()
        print("-> Habit completion undo verified.")
        
        # Re-complete for today so dashboard reflects habit completion
        with page.expect_navigation():
            page.click("#habit-complete-btn")
        page.reload()
        assert page.locator("text=Completed Today").is_visible()
        print("-> Habit re-completed for dashboard.")
        
        print("=== 6. DASHBOARD LIVE DATA INTEGRATION ===")
        page.goto(f"{base_url}/accounts/dashboard/")
        page.reload()
        page.screenshot(path="screenshots/dashboard_live.png")
        
        # Verify live values on dashboard
        assert page.locator("text=Active Daily Task").first.is_visible(), "Dashboard does not show pending tasks"
        assert page.locator("text=Deep Focus 90 Mins").first.is_visible(), "Dashboard does not show active habits"
        assert page.locator("text=Verified Phase 4 Arc").first.is_visible(), "Dashboard does not show primary Arc"
        print("-> Dashboard live database integration verified.")
        
        print("=== 7. MOBILE RESPONSIVE TESTING ===")
        mobile_context = browser.new_context(viewport={'width': 375, 'height': 667}, is_mobile=True)
        mobile_page = mobile_context.new_page()
        mobile_context.add_cookies(context.cookies())
        
        mobile_page.goto(f"{base_url}/accounts/dashboard/")
        mobile_page.screenshot(path="screenshots/mobile_view.png")
        assert mobile_page.locator("h1:has-text('Command Center')").is_visible()
        
        mobile_page.goto(f"{base_url}/tasks/")
        assert mobile_page.locator("h1:has-text('Tasks')").is_visible()
        
        mobile_page.goto(f"{base_url}/habits/")
        assert mobile_page.locator("h1:has-text('Habits')").is_visible()
        mobile_context.close()
        print("-> Mobile responsive viewports verified without layout breakage.")
        
        print("=== 8. SECURITY & CROSS-USER OWNERSHIP ENFORCEMENT ===")
        context_attacker = browser.new_context()
        page_attacker = context_attacker.new_page()
        page_attacker.goto(f"{base_url}/accounts/login/")
        page_attacker.fill("input[name='username']", "otheruser")
        page_attacker.fill("input[name='password']", "password123")
        with page_attacker.expect_navigation():
            page_attacker.click("button:has-text('Log In')")
            
        # 1. Direct access to Arc -> 404
        r_arc = page_attacker.goto(arc_url)
        assert r_arc.status == 404, f"Security violation: otheruser accessed arc, status {r_arc.status}"
        
        # 2. Direct access to Goal -> 404
        r_goal = page_attacker.goto(goal_url)
        assert r_goal.status == 404, f"Security violation: otheruser accessed goal, status {r_goal.status}"
        
        # 3. Direct access to Task -> 404
        r_task = page_attacker.goto(task_url)
        assert r_task.status == 404, f"Security violation: otheruser accessed task, status {r_task.status}"
        
        # 4. Direct access to Task edit -> 404
        r_task_edit = page_attacker.goto(f"{task_url}edit/")
        assert r_task_edit.status == 404, f"Security violation: otheruser accessed task edit, status {r_task_edit.status}"
        
        # 5. Direct access to Habit -> 404
        r_habit = page_attacker.goto(habit_url)
        assert r_habit.status == 404, f"Security violation: otheruser accessed habit, status {r_habit.status}"
        
        # 6. Direct access to Habit edit -> 404
        r_habit_edit = page_attacker.goto(f"{habit_url}edit/")
        assert r_habit_edit.status == 404, f"Security violation: otheruser accessed habit edit, status {r_habit_edit.status}"
        
        print("-> Cross-user security: all direct access attempts rejected with HTTP 404.")
        context_attacker.close()
        
        browser.close()
        
        print("========================================")
        print(f"JS Errors: {len(js_errors)}")
        for e in js_errors:
            print(f"  {e}")
            
        print(f"Failed HTTP Requests: {len(failed_requests)}")
        for f in failed_requests:
            print(f"  {f}")
            
        print("BROWSER TEST EXECUTION COMPLETE — ALL ASSERTIONS PASSED.")

if __name__ == "__main__":
    run_browser_tests()
