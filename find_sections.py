import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

urls = [
    "https://www.yenikocaeli.com",
    "https://www.bizimyaka.com"
]

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}

for url in urls:
    print(f"--- {url} ---")
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.content, "lxml")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if any(t in text.lower() for t in ["gündem", "gundem", "asayiş", "asayis", "arayis", "yerel", "yaşam", "yasam", "son dakika"]):
                print(f"Text: {text} | Link: {urljoin(url, href)}")
    except Exception as e:
        print(f"Error: {e}")
