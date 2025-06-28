import time
from playwright.sync_api import sync_playwright

def build_roster_url(base_url, sport, gender):
    """
    Build the likely roster URL based on the base athletics URL, sport, and gender.
    Example: base_url='https://gobearcats.com', sport='basketball', gender='mens'
    Result: 'https://gobearcats.com/sports/mens-basketball/roster'
    """
    sport = sport.lower()
    gender = gender.lower()
    return f"{base_url.rstrip('/')}/sports/{gender}-{sport}/roster"

def extract_roster_data(page, base_url):
    """
    Extract only valid athlete entries for any school (no hardcoded domain).
    """
    roster = []
    player_links = page.query_selector_all('a[aria-label*="View Full Bio"]')
    print(f"Found {len(player_links)} player bio links with 'View Full Bio'.")
    seen = set()
    for link in player_links:
        name = link.inner_text().strip()
        href = link.get_attribute("href")
        if href and href.startswith("http"):
            bio_url = href
        elif href and href.startswith("/"):
            bio_url = base_url.rstrip("/") + href
        elif href:
            bio_url = base_url.rstrip("/") + "/" + href
        else:
            bio_url = ""
        # Only keep entries with non-empty name, not 'Full Bio', not a coach/staff
        is_valid = (
            name and name.lower() != 'full bio' and '/coaches/' not in bio_url and '/staff/' not in bio_url
        )
        dedup_key = (name, bio_url)
        if is_valid and dedup_key not in seen:
            roster.append({"name": name, "player_bio_url": bio_url})
            seen.add(dedup_key)
    for i, entry in enumerate(roster[:3]):
        print(f"Valid player {i+1}: {entry}")
    if not roster:
        print("extract_roster_data: No valid player data extracted.")
    return roster

def scrape_roster(base_url, sport, gender):
    roster_url = build_roster_url(base_url, sport, gender)
    print(f"Visiting roster URL: {roster_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(roster_url, timeout=60000, wait_until="domcontentloaded")
        except Exception as e:
            print(f"Error loading roster page: {e}")
            browser.close()
            return {"error": f"Could not load roster: {e}", "roster": []}

        # Attempt to auto-click cookie popups using multiple likely selectors
        cookie_selectors = [
            "button#onetrust-accept-btn-handler",
            "button.cookie-accept",
            "button[aria-label='Accept cookies']",
            "button:has-text('Accept')",
            "text=Accept Cookies",
            "text=I Agree",
            "button:has-text('I Agree')",
            "button:has-text('Got it')",
            "button:has-text('Allow All')"
        ]
        for selector in cookie_selectors:
            try:
                btn = page.query_selector(selector)
                if btn and btn.is_visible():
                    btn.click()
                    print(f"Clicked cookie acceptance button: {selector}")
                    time.sleep(2)  # wait for popup to disappear
                    break
            except Exception:
                continue

        page.mouse.wheel(0, 3000)  # Scroll down to trigger lazy load
        time.sleep(10)  # Wait for JS to render player cards

        roster = extract_roster_data(page, base_url)

        browser.close()

    return roster

if __name__ == "__main__":
    # Quick manual test
    base_url = "https://gobearcats.com"
    sport = "basketball"
    gender = "mens"

    roster = scrape_roster(base_url, sport, gender)
    print("\nScraped Roster Data:")
    for athlete in roster:
        print(athlete)
