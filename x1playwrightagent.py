import time
from playwright.sync_api import sync_playwright

def build_possible_roster_paths(sport, gender):
    """
    Return a list of likely roster path patterns for a given sport/gender combo.
    """
    sport = sport.lower()
    gender = gender.lower()

    # Common patterns for NCAA and Sidearm/Presto/CMS sites
    paths = [
        f"/sports/{gender}-{sport}/roster",
        f"/sports/{sport}/roster",
        f"/roster.aspx?path={sport}",            # Presto/others
        f"/sports/{gender}{sport}/roster",
        f"/roster",                              # fallback, some small schools
        f"/team/roster",
        f"/teams/{sport}/roster",
        f"/{sport}/roster",
        f"/sports/{sport}/2023-24/roster",       # Year-specific (optional)
    ]
    # Remove duplicates while preserving order
    seen = set()
    clean_paths = []
    for p in paths:
        if p not in seen:
            clean_paths.append(p)
            seen.add(p)
    return clean_paths

def find_roster_link(page, sport):
    """
    If all else fails, scan homepage for 'roster'/'basketball' links.
    """
    sport = sport.lower()
    links = page.query_selector_all("a")
    for link in links:
        text = (link.inner_text() or "").lower()
        href = link.get_attribute("href") or ""
        if "roster" in text and sport in text and "coach" not in text and "staff" not in text:
            if href.startswith("http"):
                return href
            elif href.startswith("/"):
                base = page.url.split("/")[0] + "//" + page.url.split("/")[2]
                return base + href
    # Second pass: just find first link with "roster" and sport in href
    for link in links:
        href = (link.get_attribute("href") or "").lower()
        if "roster" in href and sport in href:
            if href.startswith("http"):
                return href
            elif href.startswith("/"):
                base = page.url.split("/")[0] + "//" + page.url.split("/")[2]
                return base + href
    return None

def is_404(page):
    # Heuristic to detect 404 or not found
    title = (page.title() or "").lower()
    if "not found" in title or "404" in title:
        return True
    # Some sites show a body message instead
    body = (page.inner_text("body") or "").lower()
    return "not found" in body or "404" in body

def extract_roster_data(page, base_url):
    """
    Try multiple selectors to handle different site layouts.
    """
    roster = []
    selectors = [
        'a[aria-label*="View Full Bio"]',
        '.sidearm-roster-player-name a',
        '.roster__player a',
        '.player-card a',
        'table tr a',
        'a[href*="bio"]',
    ]
    seen = set()
    for sel in selectors:
        player_links = []
        try:
            player_links = page.query_selector_all(sel)
        except Exception:
            continue
        for link in player_links:
            try:
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
                is_valid = (
                    name and name.lower() != 'full bio' and '/coaches/' not in bio_url and '/staff/' not in bio_url
                )
                dedup_key = (name, bio_url)
                if is_valid and dedup_key not in seen:
                    roster.append({"name": name, "player_bio_url": bio_url})
                    seen.add(dedup_key)
            except Exception:
                continue
        if roster:
            break  # Stop at first working selector with results
    return roster

def click_popups(page):
    popup_texts = [
        "accept", "agree", "got it", "ok", "close", "continue", "allow all"
    ]
    for text in popup_texts:
        try:
            btns = page.query_selector_all(f'button:has-text("{text.title()}"), button:has-text("{text.upper()}"), button:has-text("{text.lower()}")')
            for btn in btns:
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(2)
        except Exception:
            continue

def scrape_roster(base_url, sport, gender):
    possible_paths = build_possible_roster_paths(sport, gender)
    print(f"Trying paths for {base_url}: {possible_paths}")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
        click_popups(page)
        # Try each roster path
        for path in possible_paths:
            full_url = base_url.rstrip("/") + path
            print(f"Trying roster URL: {full_url}")
            try:
                page.goto(full_url, timeout=30000, wait_until="domcontentloaded")
                click_popups(page)
                page.mouse.wheel(0, 3000)
                time.sleep(6)
                if not is_404(page):
                    roster = extract_roster_data(page, base_url)
                    if roster:
                        browser.close()
                        return roster
            except Exception as e:
                print(f"Error trying path {full_url}: {e}")
                continue
        # Last resort: crawl homepage for roster link
        print("No roster found with common patterns, searching homepage for links...")
        try:
            homepage_url = base_url.rstrip("/")
            page.goto(homepage_url, timeout=30000, wait_until="domcontentloaded")
            click_popups(page)
            link = find_roster_link(page, sport)
            if link:
                print(f"Trying found roster link: {link}")
                try:
                    page.goto(link, timeout=30000, wait_until="domcontentloaded")
                    click_popups(page)
                    page.mouse.wheel(0, 3000)
                    time.sleep(6)
                    roster = extract_roster_data(page, base_url)
                    if roster:
                        browser.close()
                        return roster
                except Exception as e:
                    print(f"Error loading found roster link: {e}")
        except Exception as e:
            print(f"Error crawling homepage: {e}")
        browser.close()
        return {"error": "Could not find or load a valid roster for this school/sport/gender.", "roster": []}

if __name__ == "__main__":
    base_url = "https://gobearcats.com"
    sport = "basketball"
    gender = "mens"
    roster = scrape_roster(base_url, sport, gender)
    print("\nScraped Roster Data:")
    for athlete in roster if isinstance(roster, list) else roster.get('roster', []):
        print(athlete)
