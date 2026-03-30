import requests

h = {"User-Agent": "Mozilla/5.0 (compatible; RSS reader)", "Accept": "application/rss+xml, application/xml, text/xml"}
tests = [
    ("Ses /feed", "https://www.seskocaeli.com/feed"),
    ("Ses /feed/", "https://www.seskocaeli.com/feed/"),
    ("Cagdas /feed", "https://www.cagdaskocaeli.com.tr/feed"),
    ("Cagdas /feed/", "https://www.cagdaskocaeli.com.tr/feed/"),
    ("Ozgur /feed", "https://www.ozgurkocaeli.com.tr/feed"),
    ("Ozgur /feed/", "https://www.ozgurkocaeli.com.tr/feed/"),
    ("Yeni /feed", "https://www.yenikocaeli.com/feed"),
    ("Bizim /feed", "https://www.bizimyaka.com/feed"),
    ("Ses /rss", "https://www.seskocaeli.com/rss"),
    ("Cagdas /rss", "https://www.cagdaskocaeli.com.tr/rss"),
    ("Ozgur /rss", "https://www.ozgurkocaeli.com.tr/rss"),
]
for name, url in tests:
    try:
        r = requests.get(url, headers=h, timeout=10)
        print(f"{name}: STATUS={r.status_code} | CT={r.headers.get('Content-Type','')[:50]}")
    except Exception as e:
        print(f"{name}: ERROR - {e}")
