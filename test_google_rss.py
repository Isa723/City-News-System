"""
Test Google News RSS as bypass for blocked sites.
Google News caches articles and serves them from news.google.com — never blocked.
"""
import requests
import feedparser
from urllib.parse import quote

queries = [
    "Kocaeli kaza",
    "Kocaeli yangın",
    "Kocaeli hırsızlık",
    "Kocaeli elektrik kesintisi",
    "Kocaeli festival etkinlik",
    "seskocaeli.com",
    "cagdaskocaeli.com.tr",
    "ozgurkocaeli.com.tr site:seskocaeli.com OR site:cagdaskocaeli.com.tr OR site:ozgurkocaeli.com.tr",
]

h = {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)"}

for q in queries:
    encoded = quote(q)
    url = f"https://news.google.com/rss/search?q={encoded}&hl=tr&gl=TR&ceid=TR:tr"
    try:
        r = requests.get(url, headers=h, timeout=10)
        feed = feedparser.parse(r.content)
        print(f"\nQuery: {q}")
        print(f"  Status: {r.status_code}, Entries: {len(feed.entries)}")
        for e in feed.entries[:3]:
            print(f"  - {e.title[:70]} | {e.get('published','')[:20]}")
    except Exception as ex:
        print(f"  ERROR: {ex}")
