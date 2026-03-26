import feedparser
import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.seskocaeli.com/rss"

def check_rss():
    print(f"Checking {URL}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(URL, headers=headers, timeout=20)
    feed = feedparser.parse(resp.content)
    
    print(f"Found {len(feed.entries)} entries.")
    for entry in feed.entries:
        title = entry.title
        link = entry.link
        print(f"- {title}")
        if "Dilovası" in title or "yangın" in title.lower() or "ağıl" in title.lower():
            print(f"  *** MATCH FOUND: {title} ***")
            print(f"  Link: {link}")

if __name__ == "__main__":
    check_rss()
