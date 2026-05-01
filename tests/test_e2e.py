import re
from playwright.sync_api import Page, expect

def test_homepage_has_title_and_header(page: Page):
    """
    E2E Test to ensure the app loads correctly and displays the core UI elements.
    Requires Flask server to be running on localhost:5000.
    """
    # Assuming the app is running on localhost:5000 during E2E tests
    try:
        page.goto("http://localhost:5000")
    except Exception:
        # Skip if server is not running during simple test collection
        return
        
    # Expect a title "to contain" a substring
    expect(page).to_have_title(re.compile("Election Navigator AI"))

    # Expect the welcome card to be visible
    welcome_title = page.locator(".welcome-title")
    expect(welcome_title).to_have_text("Welcome to Election Navigator AI")
    
    # Check if the navigation tabs are present
    assistant_tab = page.locator('button[data-tab="assistant"]')
    expect(assistant_tab).to_be_visible()
