import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re

def build_possible_roster_paths(sport, gender):
    sport = sport.lower()
    gender = gender.lower()
    # List of common patterns including Presto/Sidearm/CMS edge cases
    paths = [
        f"/sports/{gender}-{sport}/roster",
        f"/sports/{sport}/roster",
        f"/roster.aspx?path={sport}",
        f"/sports/{sport}/roster.aspx",
        f"/sports/{sport}/{gender}/roster",
        f"/team/roster",
        f"/teams/{sport}/roster",
        f"/{sport}/roster",
        f"/sports/{sport}/2023-24/roster",
        f"/sports/{sport}/2022-23/roster",
        f"/roster",  # catchall
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
    sport = sport.lower()
    links = page.query_selector_all("a")
    for link in links:
        try:
            text = (link.inner_text() or "").lower()
            href = link.get_attribute("href") or ""
            if "roster" in text and sport in text and "coach" not in text and "staff" not in text:
                if href.startswith("http"):
                    return href
                elif href.startswith("/"):
                    base = page.url.split("/")[0] + "//" + page.url.split("/")[2]
                    return base + href
        except Exception:
            continue
    # Second pass: any "roster" + sport in href
    for link in links:
        try:
            href = (link.get_attribute("href") or "").lower()
            if "roster" in href and sport in href:
                if href.startswith("http"):
                    return href
                elif href.startswith("/"):
                    base = page.url.split("/")[0] + "//" + page.url.split("/")[2]
                    return base + href
        except Exception:
            continue
    return None

def is_404(page):
    try:
        title = (page.title() or "").lower()
        if "not found" in title or "404" in title:
            return True
        body = (page.inner_text("body") or "").lower()
        return "not found" in body or "404" in body
    except Exception:
        return False

def extract_roster_data(page, base_url):
    roster = []
    selectors = [
        'a[aria-label*="View Full Bio"]',
        '.sidearm-roster-player-name a',
        '.roster__player a',
        '.player-card a',
        'table tr a',
        'a[href*="bio"]',
        'tr td a',
    ]
    seen = set()
    for sel in selectors:
        try:
            player_links = page.query_selector_all(sel)
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
                        name and name.lower() != 'full bio'
                        and '/coaches/' not in bio_url and '/staff/' not in bio_url
                    )
                    dedup_key = (name, bio_url)
                    if is_valid and dedup_key not in seen:
                        roster.append({"name": name, "player_bio_url": bio_url})
                        seen.add(dedup_key)
                except Exception:
                    continue
            if roster:
                break
        except Exception:
            continue
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
        try:
            page.goto(base_url, timeout=30000, wait_until="domcontentloaded")
            click_popups(page)
        except Exception as e:
            print(f"Could not load home page: {e}")
            browser.close()
            return {"error": "Could not load the school's main athletics homepage.", "roster": []}
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
        return {"error": f"Could not find or load a valid roster for {sport} ({gender}) at this school. Please try another school or sport.", "roster": []}

def extract_player_profile_html(player_url):
    UNWANTED_TAGS = [
        'script', 'style', 'iframe', 'svg', 'path', 'noscript',
        'link', 'meta', 'object', 'embed', 'form', 'footer',
        'header', 'canvas', 'picture', 'source', 'nav'
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(player_url, timeout=30000, wait_until="domcontentloaded")
            click_popups(page)
            time.sleep(3)  # Let dynamic content load

            raw_html = page.inner_html("main")
            soup = BeautifulSoup(raw_html, "lxml")

            # Remove unwanted tags
            for tag in UNWANTED_TAGS:
                for element in soup.find_all(tag):
                    element.decompose()

            # Strip whitespace in text nodes
            for text_node in soup.find_all(string=True):
                text_node.replace_with(text_node.strip())

            # Clean up whitespace between tags
            cleaned_html = str(soup)
            cleaned_html = re.sub(r'>\s+<', '><', cleaned_html)
            cleaned_html = cleaned_html.strip()

            return cleaned_html

        except Exception as e:
            print(f"Error loading player profile: {e}")
            return None
        finally:
            browser.close()
            
if __name__ == "__main__":
    base_url = "https://www.millikinathletics.com"
    sport = "baseball"
    gender = "mens"
    roster = extract_player_profile_html('https://gohuskies.com/sports/baseball/roster/isaac-yeager/16346')
    print("\nScraped Roster Data:")
    print(roster)
