import sys
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

VIEWPORTS = [
    (320, 600, "Mobile 320px"),
    (360, 700, "Mobile 360px"),
    (390, 844, "Mobile 390px"),
    (430, 932, "Mobile 430px"),
    (1440, 900, "Desktop 1440px"),
]

# Pages to test: (url, page_name, expected_parent_link_text)
# For list pages: expected_parent_link_text is "Back to Dashboard"
# For detail/create/edit pages: parent link + dashboard link both exist
AUTHENTICATED_PAGES = [
    ("/accounts/dashboard/", "Dashboard", None),
    ("/accounts/profile/", "Profile", "Back to Dashboard"),
    ("/habits/", "Habits List", "Back to Dashboard"),
    ("/habits/34/", "Habit Detail", "Back to Habits"),
    ("/habits/new/", "Habit Create", "Back to Habits"),
    ("/habits/34/edit/", "Habit Edit", "Back to"),
    ("/tasks/", "Tasks List", "Back to Dashboard"),
    ("/tasks/73/", "Task Detail", "Back to Tasks"),
    ("/tasks/new/", "Task Create", "Back to Tasks"),
    ("/tasks/73/edit/", "Task Edit", "Back to"),
    ("/arcs/", "Arcs List", "Back to Dashboard"),
    ("/arcs/66/", "Arc Detail", "Back to Arcs"),
    ("/arcs/new/", "Arc Create", "Back to Arcs"),
    ("/arcs/66/edit/", "Arc Edit", "Back to"),
    ("/goals/30/", "Goal Detail", "Back to"),
    ("/goals/30/milestones/new/", "Milestone Create", "Back to"),
    ("/journal/", "Journal List", "Back to Dashboard"),
    ("/journal/new/", "Journal Create", "Back to Journal"),
    ("/analytics/", "Analytics", "Back to Dashboard"),
    ("/notifications/", "Notifications List", "Back to Dashboard"),
    ("/notifications/preferences/", "Notification Preferences", "Back to Notifications"),
]

def run_tests():
    console_errors = []
    failed_requests = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Login
        login_context = browser.new_context(viewport={"width": 390, "height": 844})
        page = login_context.new_page()
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
        page.on("requestfailed", lambda req: failed_requests.append(req.url))

        page.goto(f"{BASE_URL}/accounts/login/")
        page.fill('input[name="username"]', 'browseruser1')
        page.fill('input[name="password"]', 'Password123!')
        with page.expect_navigation():
            page.click('#login-submit-btn')

        print("=== 1. VERIFYING BRAND WORDMARK & AUTHENTICATED HEADER LINK ===")
        brand_link = page.locator('#global-navbar a[aria-label*="Winter Arc"]')
        brand_href = brand_link.get_attribute("href")
        print(f"Brand mark link href for authenticated user: {brand_href}")
        assert "/accounts/dashboard/" in brand_href, f"Brand link should point to dashboard, got {brand_href}"

        wordmark = brand_link.locator("span")
        box = wordmark.bounding_box()
        font_family = wordmark.evaluate("el => window.getComputedStyle(el).fontFamily")
        font_size = wordmark.evaluate("el => window.getComputedStyle(el).fontSize")
        letter_spacing = wordmark.evaluate("el => window.getComputedStyle(el).letterSpacing")
        print(f"Brand Wordmark: text='{wordmark.inner_text()}', size={font_size}, font={font_family}, spacing={letter_spacing}")

        # 2. Test Spacing & Dashboard Link Across Viewports
        print("\n=== 2. AUDITING HEADER-TO-CONTENT SPACING & DASHBOARD NAVIGATION ===")
        for vp_w, vp_h, vp_name in VIEWPORTS:
            print(f"\n--- Testing Viewport: {vp_name} ({vp_w}x{vp_h}) ---")
            page.set_viewport_size({"width": vp_w, "height": vp_h})

            for path, name, expected_parent_text in AUTHENTICATED_PAGES:
                page.goto(f"{BASE_URL}{path}")
                page.wait_for_timeout(200)

                # Check horizontal overflow
                cw = page.evaluate("document.documentElement.clientWidth")
                sw = page.evaluate("document.documentElement.scrollWidth")
                assert sw <= cw + 1, f"Horizontal overflow on {name} at {vp_w}px: scrollWidth={sw} > clientWidth={cw}"

                # Check Navbar Bounding Box
                navbar = page.locator("#global-navbar")
                nav_box = navbar.bounding_box()
                nav_bottom = nav_box["y"] + nav_box["height"]

                # Find first interactive content element (back link or first heading/card)
                back_link = page.locator(".wa-back-link").first
                if back_link.count() > 0 and back_link.is_visible():
                    target_el = back_link
                    target_name = "Back Navigation"
                else:
                    # When back link is not present or hidden on desktop (e.g. Dashboard or desktop list pages)
                    target_el = page.locator(".page-header, h1, .wa-form-card, .wa-card").first
                    target_name = "Page Header"

                target_box = target_el.bounding_box()
                assert target_box is not None, f"Target element not found on {name}"
                gap = target_box["y"] - nav_bottom

                # Spacing requirements: must be positive and >= 20px
                assert gap >= 20, (
                    f"INSUFFICIENT SPACING on {name} ({vp_name})! "
                    f"Navbar bottom={nav_bottom:.1f}px, {target_name} top={target_box['y']:.1f}px, Gap={gap:.1f}px"
                )

                # Verify Dashboard Navigation access on page
                if path != "/accounts/dashboard/":
                    # Check that a link to dashboard exists on this page
                    dash_links = page.locator('a[href*="/accounts/dashboard/"]')
                    assert dash_links.count() >= 1, f"Missing Dashboard navigation on {name}!"

                # Verify Parent link text if specified
                if expected_parent_text and path != "/accounts/dashboard/":
                    if vp_w >= 768 and expected_parent_text == "Back to Dashboard":
                        # On desktop, redundant "Back to Dashboard" must be hidden
                        dash_back = page.locator('.wa-back-link:has-text("Back to Dashboard")')
                        assert not dash_back.is_visible(), f"Redundant Back to Dashboard should be hidden on desktop for {name}!"
                    else:
                        parent_link = page.locator(f'.wa-back-link:has-text("{expected_parent_text}")')
                        assert parent_link.count() >= 1 and parent_link.first.is_visible(), (
                            f"Expected parent link containing '{expected_parent_text}' missing or hidden on {name} at {vp_w}px!"
                        )

                # Print check line
                print(f"  [PASS] [{name}]: Gap={gap:.1f}px, Overflows={sw > cw}, DashNav=OK")

        print("\n=== 3. VERIFYING MOBILE NAVBAR NOTIFICATIONS & MOBILE DRAWER ===")
        page.set_viewport_size({"width": 390, "height": 844})
        page.goto(f"{BASE_URL}/habits/34/")

        # Verify notification icon is visible directly in navbar on mobile
        mobile_nav_notif = page.locator('#global-navbar div.md\\:hidden a[href*="/notifications/"]')
        assert mobile_nav_notif.is_visible(), "Notification icon not visible in mobile navbar!"
        print("  [PASS] Notification icon is present and visible directly in the mobile navbar.")

        menu_btn = page.locator("#mobile-menu-btn")
        menu_btn.click()
        page.wait_for_timeout(200)

        # Assert no notification button in hamburger drawer
        drawer_notif = page.locator('#mobile-menu a[href*="/notifications/"]')
        assert drawer_notif.count() == 0, "Notification button should NOT be in the hamburger menu drawer!"
        print("  [PASS] Confirmed NO notification button in mobile hamburger menu drawer.")

        mobile_dash_link = page.locator('#mobile-menu a[href*="/accounts/dashboard/"]')
        assert mobile_dash_link.is_visible(), "Dashboard link not visible in mobile drawer!"
        print("  [PASS] Mobile drawer opened and exposes Dashboard destination clearly.")

        # Click the link in mobile drawer to test navigation
        with page.expect_navigation():
            mobile_dash_link.click()
        assert page.url.endswith("/accounts/dashboard/"), f"Mobile drawer failed to navigate to dashboard: {page.url}"
        print("  [PASS] Successfully navigated to Dashboard via mobile menu.")

        # Now test clicking the notification icon in mobile navbar
        page.set_viewport_size({"width": 390, "height": 844})
        mobile_nav_notif = page.locator('#global-navbar div.md\\:hidden a[href*="/notifications/"]')
        with page.expect_navigation():
            mobile_nav_notif.click()
        assert page.url.endswith("/notifications/"), f"Mobile navbar notification icon failed to navigate: {page.url}"
        print("  [PASS] Successfully navigated to Notifications via mobile navbar icon.")

        # Test in-content contextual back link and in-content Dashboard link on Habit Detail
        print("\n=== 4. TESTING DIRECT IN-PAGE NAVIGATION LINKS ===")
        page.goto(f"{BASE_URL}/habits/34/")
        
        # Test back to Habits
        with page.expect_navigation():
            page.locator('a.wa-back-link:has-text("Back to Habits")').click()
        assert page.url.endswith("/habits/"), f"Failed navigating to /habits/, got {page.url}"
        print("  [PASS] Habit Detail 'Back to Habits' successfully navigated to /habits/.")

        # On Habits List, test 'Back to Dashboard'
        with page.expect_navigation():
            page.locator('a.wa-back-link:has-text("Back to Dashboard")').click()
        assert page.url.endswith("/accounts/dashboard/"), f"Failed navigating to /accounts/dashboard/, got {page.url}"
        print("  [PASS] Habits List 'Back to Dashboard' successfully navigated to /accounts/dashboard/.")

        # On Task Detail, test direct in-page 'Dashboard' link
        page.goto(f"{BASE_URL}/tasks/73/")
        with page.expect_navigation():
            page.locator('.page-container-narrow a.wa-back-link:has-text("Dashboard")').click()
        assert page.url.endswith("/accounts/dashboard/"), f"Failed navigating to Dashboard from Task Detail, got {page.url}"
        print("  [PASS] Task Detail in-page 'Dashboard ->' link successfully navigated to /accounts/dashboard/.")

        browser.close()

    print("\n=======================================================")
    print("VERIFICATION SUMMARY")
    print("=======================================================")
    print(f"Console errors: {len(console_errors)}")
    print(f"Failed requests: {len(failed_requests)}")
    assert len(console_errors) == 0, f"Console errors detected: {console_errors}"
    assert len(failed_requests) == 0, f"Failed requests detected: {failed_requests}"
    print("ALL GLOBAL NAVIGATION & SPACING TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
