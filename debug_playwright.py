from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('http://127.0.0.1:8002/accounts/login/')
    page.fill('input[name=username]', 'browseruser')
    page.fill('input[name=password]', 'password123')
    page.click("button:has-text('Log In')")
    page.wait_for_url('**/dashboard/')
    page.goto('http://127.0.0.1:8002/arcs/')
    page.click('text=Updated Browser Arc')
    print('URL:', page.url)
    print('Buttons:', page.locator('#add-goal-btn').count())
