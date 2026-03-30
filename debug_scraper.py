"""
Quick diagnostic: visits ONE listing page per site in UC mode,
counts article links found, then tests requests fetch on the first article.
Run with: .venv\Scripts\python debug_scraper.py
"""
import re, time, random
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
from seleniumbase import SB

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

SITES = [
    ("Çağdaş",  "https://www.cagdaskocaeli.com.tr/",  r"cagdaskocaeli\.com\.tr/[\w\-]{10,}"),
    ("Özgür",   "https://www.ozgurkocaeli.com.tr/",    r"ozgurkocaeli\.com\.tr/[\w\-]{10,}"),
    ("Ses",     "https://www.seskocaeli.com/",          r"seskocaeli\.com/[\w\-]{10,}"),
    ("Yeni",    "https://www.yenikocaeli.com/",         r"yenikocaeli\.com/[\w\-]{10,}"),
    ("Bizim",   "https://www.bizimyaka.com/",           r"bizimyaka\.com/[\w\-]{10,}"),
]

JUNK = re.compile(r"#|javascript|mailto|\.pdf|\.jpg|\.png|/wp-|/feed|/tag/|/author/|/page/|/sayfa/", re.I)

with SB(uc=True, headless=False, incognito=True) as sb:
    for name, url, pat in SITES:
        print(f"\n{'='*60}")
        print(f"[{name}] Opening: {url}")
        try:
            sb.uc_open_with_reconnect(url, reconnect_time=3)
            time.sleep(2)
            html = sb.get_page_source()
            soup = BeautifulSoup(html, "lxml")
            page_title = soup.title.get_text(strip=True) if soup.title else "???"
            print(f"  Page title: {page_title}")

            # Collect links
            links = []
            art_re = re.compile(pat, re.I)
            for a in soup.find_all("a", href=True):
                href = a["href"].strip()
                full = urljoin(url, href)
                if JUNK.search(full): continue
                if not art_re.search(full): continue
                parsed = urlparse(full)
                clean = parsed.scheme + "://" + parsed.netloc + parsed.path.rstrip("/")
                if clean not in links:
                    links.append(clean)

            print(f"  Article links found: {len(links)}")
            for l in links[:5]:
                print(f"    {l}")

            if links:
                # Export cookies
                session = requests.Session()
                for c in sb.driver.get_cookies():
                    session.cookies.set(c["name"], c["value"], domain=c.get("domain",""))
                ua = sb.driver.execute_script("return navigator.userAgent;")
                session.headers.update({"User-Agent": ua, **HEADERS})

                # Test fetch on first article
                test_url = links[0]
                print(f"\n  Testing requests fetch: {test_url}")
                resp = session.get(test_url, timeout=12, allow_redirects=True)
                print(f"  Status: {resp.status_code}")
                if resp.status_code == 200:
                    s2 = BeautifulSoup(resp.content, "lxml")
                    h1 = s2.find("h1")
                    print(f"  H1: {h1.get_text(strip=True)[:100] if h1 else 'NOT FOUND'}")
                else:
                    print(f"  ❌ Still blocked even with cookies!")
        except Exception as e:
            print(f"  ERROR: {e}")

print("\nDone.")
