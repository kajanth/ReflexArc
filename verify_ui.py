import os
from playwright.sync_api import sync_playwright

def run_cuj(page):
    cwd = os.getcwd()
    page.goto(f"file://{cwd}/web/dashboard.html")
    page.wait_for_timeout(500)

    # 1. Test clicking the "☀️ AWAKE" button
    page.get_by_role("button", name="☀️ AWAKE").click()
    page.wait_for_timeout(500)

    # 2. Test clicking API console tab
    page.get_by_role("button", name="⚡ API Console").click()
    page.wait_for_timeout(500)

    # 3. Test API Endpoint button selection via keyboard focus & click
    endpoint_btn = page.locator(".api-ep-item").first
    endpoint_btn.focus()
    page.wait_for_timeout(500)
    endpoint_btn.click()
    page.wait_for_timeout(500)

    # 4. Take screenshot of the API console with endpoint focused
    page.screenshot(path="/home/jules/verification/screenshots/verification.png")
    page.wait_for_timeout(1000)

if __name__ == "__main__":
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            record_video_dir="/home/jules/verification/videos"
        )
        page = context.new_page()
        try:
            run_cuj(page)
        finally:
            context.close()
            browser.close()
