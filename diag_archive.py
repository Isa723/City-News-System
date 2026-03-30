import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}

urls = [
    "https://www.cagdaskocaeli.com.tr/arsiv/kocaeli-gundem-haberleri",
    "https://www.ozgurkocaeli.com.tr/arsiv/kocaeli-haberleri",
    "https://www.seskocaeli.com/arsiv/kocaeli-son-dakika-haberler"
]

for url in urls:
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        print(f"URL: {url} -> Status: {r.status_code}")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            links = [a['href'] for a in soup.find_all('a', href=True) if '/haber/' in a['href']]
            print(f"   Found {len(links)} links containing '/haber/' in HTML.")
            # Print first few links
            for l in links[:3]: print(f"     {l}")
        else:
            print(f"   HTML snippet: {r.text[:200]}")
    except Exception as e:
        print(f"   Error: {e}")
