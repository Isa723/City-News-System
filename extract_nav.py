import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

urls = [
    "https://www.yenikocaeli.com",
    "https://www.bizimyaka.com",
    "https://www.ozgurkocaeli.com.tr",
    "https://www.cagdaskocaeli.com.tr",
    "https://www.seskocaeli.com"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
}

targets = ["gündem", "gundem", "asayiş", "asayis", "arayis", "yerel", "yaşam", "yasam", "son dakika", "güncel", "guncel", "polis"]

for url in urls:
    print(f"\n=== {url} ===")
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
            continue
            
        soup = BeautifulSoup(resp.content, "lxml")
        # Look specifically in <nav> or <ul> or <li> for menu items
        links_found = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True).lower()
            href = a["href"]
            if any(t in text for t in targets):
                links_found.append((text, urljoin(url, href)))
        
        # Remove duplicates and print
        seen = set()
        for text, link in links_found:
            if link not in seen:
                print(f"[{text}] -> {link}")
                seen.add(link)
                
    except Exception as e:
        print(f"Error: {e}")
