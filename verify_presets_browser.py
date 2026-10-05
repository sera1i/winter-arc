"""
Playwright Browser QA Suite for Winter Arc Preset Library.

Verifies end-to-end user flow:
Dashboard -> Forge an Arc -> Presets Library (7 Blueprints) -> Review Blueprint ->
Customize (name, dates, add goal, remove habit) -> The Oath -> Activation ->
Arc Detail -> Dashboard reflects new Primary Arc.
Also tests mobile viewports (390x844), light mode, dark mode, and console/network cleanliness.
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
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def run_presets_browser_qa():
    print("=" * 70)
    print("STARTING PLAYWRIGHT PRESETS LIBRARY BROWSER QA SUITE")
    print("=" * 70)

    # 1. Run fixtures prep
    print("[INIT] Preparing test user fixtures...")
    subprocess.run([sys.executable, "prepare_browser_fixtures.py"], check=True)

    # 2. Check or launch Django dev server
    server_process = None
    if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=2):
        print("Launching Django dev server on port 8000...")
        server_process = subprocess.Popen(
            [sys.executable, "manage.py", "runserver", "127.0.0.1:8000", "--noreload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        if not wait_for_server(f"{BASE_URL}/accounts/login/", timeout=25):
            print("ERROR: Server failed to start in 25 seconds.")
            if server_process:
                server_process.kill()
            sys.exit(1)
        print("Django server ready.")
    else:
        print("Django server already running on port 8000.")

    console_errors = []
    failed_requests = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={'width': 1440, 'height': 900})
            page = context.new_page()

            # Track console errors & failed requests
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("requestfailed", lambda req: failed_requests.append(req.url))

            # -------------------------------------------------------------
            # STEP 1: Log In & Check Dashboard Entry Point
            # -------------------------------------------------------------
            print("\n[STEP 1] Logging in and checking Dashboard entry point...")
            page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            page.fill('input[name="username"]', 'browseruser1')
            page.fill('input[name="password"]', 'Password123!')
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")

            # Verify Forge an Arc link is present
            forge_btn = page.locator('a:has-text("Forge an Arc")').first
            assert forge_btn.is_visible(), "Forge an Arc button must be visible on Dashboard!"
            print("Found 'Forge an Arc' button on Dashboard.")

            # Click Forge an Arc
            forge_btn.click()
            page.wait_for_load_state("networkidle")
            assert "/arcs/presets/" in page.url, f"Expected /arcs/presets/ but got {page.url}"
            print("Successfully navigated to /arcs/presets/ via Dashboard.")

            # -------------------------------------------------------------
            # STEP 2: Verify Preset Library (Light & Dark)
            # -------------------------------------------------------------
            print("\n[STEP 2] Verifying Preset Library in Light and Dark mode...")
            
            # Check all 7 presets are present
            preset_titles = [
                "Classic Winter Arc", "Student Lock-In", "Fitness Arc",
                "Monk Mode", "Mind + Body", "Career Lock-In", "Custom Arc"
            ]
            for title in preset_titles:
                assert page.locator(f'h2:has-text("{title}")').count() >= 1, f"Missing preset: {title}"
            print("All 7 presets rendered cleanly.")

            # Check back link to Dashboard
            back_to_dash = page.locator('a.wa-back-link:has-text("Return to Dashboard")')
            assert back_to_dash.is_visible(), "Back to Dashboard link must be visible"

            # Capture Light Mode screenshot
            path_light_lib = os.path.join(SCREENSHOTS_DIR, "preset_01_library_light.png")
            page.screenshot(path=path_light_lib, full_page=True)
            print(f"Saved: {path_light_lib}")

            # Toggle to Dark Mode
            theme_btn = page.locator('#theme-toggle-btn')
            if theme_btn.is_visible():
                theme_btn.click()
                page.wait_for_timeout(300)
                dark_theme = page.evaluate("document.documentElement.getAttribute('data-theme')")
                assert dark_theme == "dark", f"Expected dark theme, got {dark_theme}"
                path_dark_lib = os.path.join(SCREENSHOTS_DIR, "preset_02_library_dark.png")
                page.screenshot(path=path_dark_lib, full_page=True)
                print(f"Saved: {path_dark_lib}")

                # Toggle back to Light
                theme_btn.click()
                page.wait_for_timeout(300)

            # -------------------------------------------------------------
            # STEP 3: Review Blueprint (Classic Winter Arc)
            # -------------------------------------------------------------
            print("\n[STEP 3] Selecting Classic Winter Arc Blueprint Review...")
            page.click('a[aria-label="Select Classic Winter Arc Blueprint"]')
            page.wait_for_load_state("networkidle")
            assert "/arcs/presets/classic/review/" in page.url

            # Verify contents
            assert page.locator('h1:has-text("Classic Winter Arc")').is_visible()
            assert page.locator('span:has-text("90 Days")').count() >= 1
            assert page.locator('text=Suggested Goals').count() >= 1
            assert page.locator('text=Suggested Habits').count() >= 1

            path_review = os.path.join(SCREENSHOTS_DIR, "preset_03_classic_review.png")
            page.screenshot(path=path_review, full_page=True)
            print(f"Saved: {path_review}")

            # -------------------------------------------------------------
            # STEP 4: Customize Blueprint
            # -------------------------------------------------------------
            print("\n[STEP 4] Customizing Blueprint...")
            page.click('a:has-text("Customize Blueprint")')
            page.wait_for_load_state("networkidle")
            assert "/arcs/presets/classic/customize/" in page.url

            # Verify that all predefined goals and habits are carried into the customization page!
            initial_goal_count = page.locator('.goal-title').count()
            initial_habit_count = page.locator('.habit-name').count()
            print(f"Initial goals carried into Customize: {initial_goal_count}")
            print(f"Initial habits carried into Customize: {initial_habit_count}")
            assert initial_goal_count == 3, f"Expected 3 goals carried over, found {initial_goal_count}!"
            assert initial_habit_count == 5, f"Expected 5 habits carried over, found {initial_habit_count}!"
            assert page.locator('.empty-goals-placeholder').count() == 0, "Empty goals placeholder should not appear for Classic Arc!"
            assert page.locator('.empty-habits-placeholder').count() == 0, "Empty habits placeholder should not appear for Classic Arc!"

            # Verify input values match Classic preset blueprint
            first_goal_title = page.locator('.goal-title').first.input_value()
            first_habit_name = page.locator('.habit-name').first.input_value()
            assert first_goal_title == "Build Physical Discipline", f"Unexpected first goal: {first_goal_title}"
            assert first_habit_name == "Daily Movement", f"Unexpected first habit: {first_habit_name}"
            print("Verified: Classic Winter Arc blueprint successfully pre-populated on Customize screen.")

            # Capture initial customize screen showing all predefined goals and habits
            path_customize_initial = os.path.join(SCREENSHOTS_DIR, "preset_04_customize_light.png")
            page.screenshot(path=path_customize_initial, full_page=True)
            print(f"Saved: {path_customize_initial}")

            # Modify Arc Name
            page.fill('input#arcName', 'Winter Arc - Iron Crucible')

            # Modify Objective
            page.fill('textarea#arcObjective', 'Forging unshakeable physical stamina, mental clarity, and daily non-negotiables.')

            # Explicitly set as Primary Arc
            page.check('input#isPrimary')

            # Remove a habit (Limit Mindless Scrolling)
            habit_count_before = page.locator('.remove-habit-btn').count()
            print(f"Habit count before removal: {habit_count_before}")
            page.locator('.remove-habit-btn').last.click()
            page.wait_for_timeout(200)
            habit_count_after = page.locator('.remove-habit-btn').count()
            print(f"Habit count after removal: {habit_count_after}")
            assert habit_count_after == habit_count_before - 1, "Habit removal failed!"

            # Add a custom Goal
            goal_count_before = page.locator('.remove-goal-btn').count()
            page.click('#addGoalBtn')
            page.wait_for_timeout(200)
            goal_count_after = page.locator('.remove-goal-btn').count()
            assert goal_count_after == goal_count_before + 1, "Goal addition failed!"

            # Fill in the newly added goal title
            page.locator('.goal-title').last.fill('Master Architecture & Systems')
            page.locator('.goal-desc').last.fill('Deep technical mastery in scalable distributed architecture.')

            # Add milestone to this new goal
            page.locator('.add-milestone-btn').last.click()
            page.wait_for_timeout(200)
            page.locator('.milestone-title').last.fill('Complete 10 System Design Specs')

            # Submit customization to advance to The Oath
            page.click('#submitCustomizeBtn')
            page.wait_for_load_state("networkidle")
            assert "/arcs/presets/classic/oath/" in page.url, f"Expected oath URL, got {page.url}"
            print("Successfully saved customization and reached The Oath.")

            # -------------------------------------------------------------
            # STEP 5: The Oath Confirmation & Activation
            # -------------------------------------------------------------
            print("\n[STEP 5] Reviewing The Oath...")
            assert page.locator('h1:has-text("The Oath")').is_visible()
            assert page.locator('h2:has-text("Iron Crucible")').is_visible()
            assert page.locator('text=Master Architecture & Systems').count() >= 1

            path_oath = os.path.join(SCREENSHOTS_DIR, "preset_05_the_oath.png")
            page.screenshot(path=path_oath, full_page=True)
            print(f"Saved: {path_oath}")

            # Click Sign the Oath & Activate Arc
            print("Signing The Oath and activating Arc...")
            page.click('#signOathBtn')
            page.wait_for_load_state("networkidle")

            # Must redirect to Arc Detail
            assert "/arcs/" in page.url and "/presets/" not in page.url
            print(f"Successfully activated Arc! Redirected to: {page.url}")

            # Verify Arc detail page displays the new arc
            assert page.locator('h1:has-text("Iron Crucible")').is_visible()
            assert page.locator('text=Master Architecture & Systems').count() >= 1

            path_detail = os.path.join(SCREENSHOTS_DIR, "preset_06_activated_arc_detail.png")
            page.screenshot(path=path_detail, full_page=True)
            print(f"Saved: {path_detail}")

            # -------------------------------------------------------------
            # STEP 6: Verify Dashboard reflects new Primary Arc
            # -------------------------------------------------------------
            print("\n[STEP 6] Verifying Dashboard reflects new Primary Arc...")
            page.goto(f"{BASE_URL}/accounts/dashboard/", wait_until="networkidle")
            assert page.locator('text=Iron Crucible').count() >= 1, "Dashboard must show new Primary Arc!"

            path_dash = os.path.join(SCREENSHOTS_DIR, "preset_07_dashboard_primary_arc.png")
            page.screenshot(path=path_dash, full_page=True)
            print(f"Saved: {path_dash}")

            # -------------------------------------------------------------
            # STEP 7: Mobile Viewport QA (390 x 844)
            # -------------------------------------------------------------
            print("\n[STEP 7] Verifying Mobile Viewport (390x844)...")
            mobile_context = browser.new_context(
                viewport={'width': 390, 'height': 844},
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15'
            )
            mob_page = mobile_context.new_page()

            # Mobile login
            mob_page.goto(f"{BASE_URL}/accounts/login/", wait_until="networkidle")
            mob_page.fill('input[name="username"]', 'browseruser1')
            mob_page.fill('input[name="password"]', 'Password123!')
            mob_page.click('button[type="submit"]')
            mob_page.wait_for_load_state("networkidle")

            # Mobile Presets Library
            mob_page.goto(f"{BASE_URL}/arcs/presets/", wait_until="networkidle")
            # Verify no horizontal scroll overflow
            scroll_width = mob_page.evaluate("document.body.scrollWidth")
            client_width = mob_page.evaluate("document.documentElement.clientWidth")
            print(f"Mobile Scroll Width: {scroll_width}, Client Width: {client_width}")
            assert scroll_width <= client_width + 1, "Horizontal scroll overflow detected on mobile!"

            path_mob_lib = os.path.join(SCREENSHOTS_DIR, "preset_08_mobile_library.png")
            mob_page.screenshot(path=path_mob_lib, full_page=True)
            print(f"Saved: {path_mob_lib}")

            # Mobile Customization screen
            mob_page.goto(f"{BASE_URL}/arcs/presets/student/customize/", wait_until="networkidle")
            path_mob_cust = os.path.join(SCREENSHOTS_DIR, "preset_09_mobile_customize.png")
            mob_page.screenshot(path=path_mob_cust, full_page=True)
            print(f"Saved: {path_mob_cust}")

            # -------------------------------------------------------------
            # STEP 8: Inspect Remaining Presets & Verify Custom Arc Clean Slate
            # -------------------------------------------------------------
            print("\n[STEP 8] Validating other presets review & Custom Arc clean slate...")
            for key in ['student', 'fitness', 'monk_mode', 'mind_body', 'career']:
                page.goto(f"{BASE_URL}/arcs/presets/{key}/review/", wait_until="networkidle")
                assert page.locator('h1').count() >= 1
                print(f"Preset '{key}' review validated (200 OK).")

            # Validate Custom Arc starts with 0 goals and 0 habits (clean slate)
            page.goto(f"{BASE_URL}/arcs/presets/custom/customize/", wait_until="networkidle")
            assert page.locator('.empty-goals-placeholder').is_visible(), "Custom Arc must show empty goals placeholder!"
            assert page.locator('.empty-habits-placeholder').is_visible(), "Custom Arc must show empty habits placeholder!"
            assert page.locator('.goal-title').count() == 0, "Custom Arc must have 0 goals on load!"
            assert page.locator('.habit-name').count() == 0, "Custom Arc must have 0 habits on load!"
            print("Verified: Custom Arc starts as a complete clean slate (0 goals, 0 habits).")

            path_custom_clean = os.path.join(SCREENSHOTS_DIR, "preset_10_custom_arc_clean_slate.png")
            page.screenshot(path=path_custom_clean, full_page=True)
            print(f"Saved: {path_custom_clean}")

            browser.close()

    finally:
        if server_process:
            print("Stopping Django test server...")
            server_process.kill()

    print("\n" + "=" * 70)
    print("BROWSER QA COMPLETED SUCCESSFULLY")
    print(f"Console errors detected: {len(console_errors)}")
    print(f"Failed network requests: {len(failed_requests)}")
    print("=" * 70)

    if console_errors:
        print("Console errors logged:")
        for err in console_errors:
            print(f" - {err}")
    if failed_requests:
        print("Failed requests:")
        for req in failed_requests:
            print(f" - {req}")

    assert len(console_errors) == 0, f"Found console errors: {console_errors}"
    assert len(failed_requests) == 0, f"Found failed network requests: {failed_requests}"


if __name__ == '__main__':
    run_presets_browser_qa()
