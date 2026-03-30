import requests
from bs4 import BeautifulSoup
import re

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

def test_article(url):
    print(f"Testing URL: {url}")
    r = requests.get(url, headers=HEADERS, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code != 200: return
    
    s = BeautifulSoup(r.text, "lxml")
    
    # Title
    og = s.find("meta", property="og:title")
    title = og["content"] if og and og.get("content") else (s.find("h1").get_text(strip=True) if s.find("h1") else "???")
    print(f"Title: {title}")
    
    # Content
    c_div = s.select_one(".news-content, .article-content, .entry-content, article, .haber-metni, .habericerik")
    if c_div:
        paras = [p.get_text(strip=True) for p in c_div.find_all("p") if len(p.get_text(strip=True)) > 20]
        content = " ".join(paras)
    else:
        content = "(Selector failed)"
    
    print(f"Content Length: {len(content)}")
    print(f"Content Snippet: {content[:300]}")

test_article("https://www.cagdaskocaeli.com.tr/haber/27706619/kocaelide-engelsiz-sanat")
