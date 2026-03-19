from playwright.sync_api import sync_playwright
import os

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(f"file://{os.path.abspath('web/dashboard.html')}")

    # Click API Console tab
    page.click("#tab-api")

    # Wait for the API endpoints to load
    page.wait_for_selector(".api-ep-item")

    # Click an endpoint to generate history (though backend is down, we might get an error but it will show in history)
    page.click(".api-ep-item")
    page.click("#api-run-btn")

    # Wait a bit
    page.wait_for_timeout(1000)

    page.screenshot(path="dashboard_api_tab.png")

    browser.close()
