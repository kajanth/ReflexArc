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

    # Use keyboard to tab down into the endpoints
    # To get to the first endpoint, we might need a few tabs from the start
    page.focus("#api-search")
    page.keyboard.press("Tab")

    # Wait a bit
    page.wait_for_timeout(500)

    page.screenshot(path="dashboard_api_focus.png")

    browser.close()
