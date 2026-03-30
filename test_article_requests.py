import requests
from bs4 import BeautifulSoup
import re

SITES = [
    {"name": "Çağdaş", "url": "https://www.cagdaskocaeli.com.tr/gundem/"},
    {"name": "Özgür", "url": "https://www.ozgurkocaeli.com.tr/gundem/"},
    {"name": "Ses", "url": "https://www.seskocaeli.com/guncel/"},
    {"name": "Yeni", "url": "https://www.yenikocaeli.com/gundem/"},
    {"name": "Bizim", "url": "https://www.bizimyaka.com/gundem/"}
]

headers = {"User-Agent": "Mozilla/5.0"}

print("Testing Article Content Fetch with simple requests...")

for site in SITES:
    try:
        # Step 1: Get listing page
        r = requests.get(site["url"], headers=headers, timeout=10)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            # Find first link that looks like an article
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                # Rough check for article link
                if re.search(r"/\d{4,}/|/haber/|/gundem/", href):
                    if href.startswith("/"):
                         href = site["url"].split(".tr/")[0] + ".tr" + href if ".tr" in site["url"] else site["url"].split(".com/")[0] + ".com" + href
                    links.append(href)
            
            if links:
                test_url = links[0]
                print(f"{site['name']} -> Listing OK. Testing article: {test_url}")
                art_r = requests.get(test_url, headers=headers, timeout=10)
                print(f"   Article Status: {art_r.status_code}, Length: {len(art_r.text)}")
            else:
                 print(f"{site['name']} -> Listing OK, but no article links found.")
        else:
             print(f"{site['name']} -> Listing FAILED: {r.status_code}")
    except Exception as e:
        print(f"{site['name']} -> Error {e}")
