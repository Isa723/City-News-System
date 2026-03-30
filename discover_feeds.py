"""
Find RSS/feed links from the news sites homepage links.
"""
import requests
from bs4 import BeautifulSoup

SITES = [
    ("Ses Kocaeli", "https://www.seskocaeli.com"),
    ("Cagdas Kocaeli", "https://www.cagdaskocaeli.com.tr"),
    ("Ozgur Kocaeli", "https://www.ozgurkocaeli.com.tr"),
    ("Yeni Kocaeli", "https://www.yenikocaeli.com"),
    ("Bizim Yaka", "https://www.bizimyaka.com"),
]

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.google.com/search?q=kocaeli+haber",
}

for name, base in SITES:
    print(f"\n=== {name} ({base}) ===")
    try:
        r = requests.get(base, headers=h, timeout=15)
        print(f"  Homepage: {r.status_code}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.content, "lxml")
            # Look for feed links in the <head>
            rss_links = soup.find_all("link", type=lambda t: t and ("rss" in t.lower() or "atom" in t.lower()))
            for link in rss_links:
                print(f"  FEED FOUND: {link.get('href')} ({link.get('title','')})")
    except Exception as e:
        print(f"  ERROR: {e}")
