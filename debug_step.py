from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    c = b.new_context()
    page = c.new_page()
    page.on('response', lambda res: print(f"HTTP {res.status}: {res.url}"))

    page.goto('http://127.0.0.1:8000/accounts/login/')
    page.fill('input[name="username"]', 'warrior_qa')
    page.fill('input[name="password"]', 'Password123!')
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)
    print("Logged in, URL:", page.url)

    page.goto('http://127.0.0.1:8000/arcs/new/')
    print("At arcs/new/, URL:", page.url)
    page.fill('input[name="name"]', 'First Arc')
    page.fill('textarea[name="objective"]', 'Test Objective')
    page.fill('input[name="start_date"]', '2026-10-01')
    page.fill('input[name="end_date"]', '2026-12-31')
    page.click('button[type="submit"]')
    page.wait_for_timeout(1500)
    print("After arc submit, URL:", page.url)
    print("Body text snippet:", page.inner_text('body')[:250])

    page.goto('http://127.0.0.1:8000/habits/new/')
    print("At habits/new/, URL:", page.url)
    print("Body text snippet:", page.inner_text('body')[:250])

    b.close()
