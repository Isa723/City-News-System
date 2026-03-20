import feedparser
import requests

RSS_FEEDS = {
    "Çağdaş Kocaeli": "https://www.cagdaskocaeli.com.tr/rss",
    "Özgür Kocaeli": "https://www.ozgurkocaeli.com.tr/rss",
    "Ses Kocaeli": "https://www.seskocaeli.com/rss",
    "Yeni Kocaeli": "https://www.yenikocaeli.com/rss",
    "Bizim Yaka": "https://www.bizimyaka.com/rss"
}

print("Starting quick feed diagnosis...")

for name, url in RSS_FEEDS.items():
    print(f"--- Testing: {name} ({url}) ---")
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, timeout=10)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.content)
            print(f"  -> [OK] Reached site. Found {len(feed.entries)} news entries in the RSS.")
            if len(feed.entries) > 0:
                print(f"  -> [INFO] Sample Title: {getattr(feed.entries[0], 'title', 'No Title')}")
        else:
            print(f"  -> [FAIL] HTTP Error: {resp.status_code}")
            
    except requests.exceptions.Timeout:
        print("  -> [FAIL] Connection timed out (Site is extremely slow or down).")
    except Exception as e:
        print(f"  -> [FAIL] Error: {e}")
    print()
