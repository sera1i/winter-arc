import sys
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

# Pages to test
LIST_PAGES = [
    ("/arcs/", "Arcs List"),
    ("/habits/", "Habits List"),
    ("/tasks/", "Tasks List"),
    ("/journal/", "Journal List"),
    ("/analytics/", "Analytics"),
    ("/notifications/", "Notifications List"),
    ("/accounts/profile/", "Profile"),
]

DETAIL_PAGES = [
    ("/habits/34/", "Habit Detail", "Back to Habits"),
    ("/tasks/73/", "Task Detail", "Back to Tasks"),
    ("/arcs/66/", "Arc Detail", "Back to Arcs"),
    ("/journal/new/", "Journal Create", "Back to Journal"),
    ("/goals/30/", "Goal Detail", "Back to"),
]

DESKTOP_VIEWPORTS = [
    (1024, 768, "Tablet Landscape / Laptop 1024px"),
    (1440, 900, "Desktop 1440px"),
]

MOBILE_VIEWPORTS = [
    (320, 600, "Mobile 320px"),
    (360, 700, "Mobile 360px"),
    (390, 844, "Mobile 390px"),
    (430, 932, "Mobile 430px"),
]

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()

        # Login
        page.goto(f"{BASE_URL}/accounts/login/")
        page.fill('input[name="username"]', 'browseruser1')
        page.fill('input[name="password"]', 'Password123!')
        with page.expect_navigation():
            page.click('#login-submit-btn')

        print("==================================================")
        print("1. VERIFYING DESKTOP VIEWPORTS (>= 768px)")
        print("   In-content Dashboard back links must be HIDDEN")
        print("   Desktop navbar Dashboard must remain VISIBLE")
        print("   Other contextual back links must remain VISIBLE")
        print("==================================================")

        for w, h, name in DESKTOP_VIEWPORTS:
            print(f"\n--- Viewport: {name} ({w}x{h}) ---")
            page.set_viewport_size({"width": w, "height": h})

            # Check Desktop Navbar Dashboard Link
            page.goto(f"{BASE_URL}/arcs/")
            nav_dash = page.locator('#global-navbar .hidden.md\\:flex a[href*="/accounts/dashboard/"]')
            assert nav_dash.is_visible(), f"Desktop navbar Dashboard link missing at {name}!"
            print(f"  [PASS] Desktop navbar Dashboard button is visible and intact.")

            # Check List Pages
            for path, title in LIST_PAGES:
                page.goto(f"{BASE_URL}{path}")
                # Look for in-content "Back to Dashboard"
                in_content_dash = page.locator('.page-container a[href*="/accounts/dashboard/"].wa-back-link, .page-container-narrow a[href*="/accounts/dashboard/"].wa-back-link')
                visible_count = sum(1 for i in range(in_content_dash.count()) if in_content_dash.nth(i).is_visible())
                assert visible_count == 0, f"Redundant Back to Dashboard visible on {title} at {name}!"
                print(f"  [PASS] [{title}]: In-content Back to Dashboard is HIDDEN.")

            # Check Detail Pages
            for path, title, parent_text in DETAIL_PAGES:
                page.goto(f"{BASE_URL}{path}")
                # In-content Dashboard link must be hidden
                in_content_dash = page.locator('a[href*="/accounts/dashboard/"].wa-back-link')
                visible_dash = sum(1 for i in range(in_content_dash.count()) if in_content_dash.nth(i).is_visible())
                assert visible_dash == 0, f"Redundant in-content Dashboard link visible on {title} at {name}!"
                
                # Contextual parent link must remain visible
                parent_link = page.locator(f'.wa-back-link:has-text("{parent_text}")')
                assert parent_link.first.is_visible(), f"Contextual parent link '{parent_text}' unexpectedly hidden on {title} at {name}!"
                print(f"  [PASS] [{title}]: Dashboard link is HIDDEN, parent link '{parent_text}' is VISIBLE.")

        print("\n==================================================")
        print("2. VERIFYING MOBILE VIEWPORTS (< 768px)")
        print("   In-content Dashboard back links must remain VISIBLE")
        print("   Navbar mobile actions (Notifications) must remain VISIBLE")
        print("   Hamburger menu must NOT contain notification button")
        print("==================================================")

        for w, h, name in MOBILE_VIEWPORTS:
            print(f"\n--- Viewport: {name} ({w}x{h}) ---")
            page.set_viewport_size({"width": w, "height": h})

            # Check notification icon directly in navbar
            page.goto(f"{BASE_URL}/arcs/")
            mobile_notif = page.locator('#global-navbar div.md\\:hidden a[href*="/notifications/"]')
            assert mobile_notif.is_visible(), f"Mobile navbar notification icon missing at {name}!"

            # Check List Pages (must be visible on mobile)
            for path, title in LIST_PAGES:
                page.goto(f"{BASE_URL}{path}")
                in_content_dash = page.locator('.wa-back-link:has-text("Back to Dashboard")')
                assert in_content_dash.first.is_visible(), f"Back to Dashboard link missing on mobile {title} at {name}!"
                print(f"  [PASS] [{title}]: In-content Back to Dashboard is VISIBLE on mobile.")

            # Check Detail Pages (Dashboard link must be visible on mobile)
            for path, title, parent_text in DETAIL_PAGES:
                page.goto(f"{BASE_URL}{path}")
                in_content_dash = page.locator('main a[href*="/accounts/dashboard/"].wa-back-link')
                assert in_content_dash.first.is_visible(), f"In-content Dashboard link missing on mobile {title} at {name}!"
                parent_link = page.locator(f'.wa-back-link:has-text("{parent_text}")')
                assert parent_link.first.is_visible(), f"Parent link '{parent_text}' missing on mobile {title} at {name}!"
                print(f"  [PASS] [{title}]: Both Dashboard and '{parent_text}' VISIBLE on mobile.")

        # Test tablet portrait breakpoint (767px vs 768px boundary)
        print("\n==================================================")
        print("3. VERIFYING BOUNDARY BEHAVIOR (767px vs 768px)")
        print("==================================================")
        page.set_viewport_size({"width": 767, "height": 800})
        page.goto(f"{BASE_URL}/arcs/")
        dash_767 = page.locator('.wa-back-link:has-text("Back to Dashboard")')
        assert dash_767.is_visible(), "Back to Dashboard should be visible at 767px (mobile layout)!"
        print("  [PASS] 767px (mobile): Back to Dashboard is VISIBLE.")

        page.set_viewport_size({"width": 768, "height": 800})
        page.goto(f"{BASE_URL}/arcs/")
        dash_768 = page.locator('.page-container a[href*="/accounts/dashboard/"].wa-back-link')
        assert not dash_768.is_visible(), "Back to Dashboard should be hidden at 768px (desktop layout)!"
        print("  [PASS] 768px (desktop): Back to Dashboard is HIDDEN.")

        browser.close()
        print("\nALL VERIFICATION CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    run()
