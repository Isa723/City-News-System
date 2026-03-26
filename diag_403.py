import requests
import sys

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,tr;q=0.8",
}

urls = [
    "https://www.cagdaskocaeli.com.tr",
    "https://www.ozgurkocaeli.com.tr",
    "https://www.seskocaeli.com"
]

for url in urls:
    print(f"--- {url} ---")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            # Print a snippet of the menu/nav if possible
            print(resp.text[:2000])
    except Exception as e:
        print(f"Error: {e}")
