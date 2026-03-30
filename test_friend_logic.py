import requests

SITES = [
    {"name": "Çağdaş", "url": "https://www.cagdaskocaeli.com.tr/arsiv/"},
    {"name": "Özgür", "url": "https://www.ozgurkocaeli.com.tr/arsiv/"},
    {"name": "Ses", "url": "https://www.seskocaeli.com/arsiv/"},
    {"name": "Yeni", "url": "https://www.yenikocaeli.com/arsiv/"},
    {"name": "Bizim", "url": "https://www.bizimyaka.com/arsiv/"}
]

# Friend's suggested header
headers = {"User-Agent": "Mozilla/5.0"}

print("Testing 'arsiv' URLs with simple requests...")

for site in SITES:
    try:
        # try simple request
        resp = requests.get(site["url"], headers=headers, timeout=10)
        print(f"{site['name']}: {site['url']} -> Status {resp.status_code}")
        if resp.status_code == 200:
             print(f"   Success! Length: {len(resp.text)}")
    except Exception as e:
        print(f"{site['name']}: {site['url']} -> Error {e}")

# Also try category URLs
print("\nTesting 'gundem' categories...")
CATS = [
    {"name": "Çağdaş", "url": "https://www.cagdaskocaeli.com.tr/gundem/"},
    {"name": "Özgür", "url": "https://www.ozgurkocaeli.com.tr/gundem/"},
    {"name": "Ses", "url": "https://www.seskocaeli.com/guncel/"},
    {"name": "Yeni", "url": "https://www.yenikocaeli.com/gundem/"},
    {"name": "Bizim", "url": "https://www.bizimyaka.com/gundem/"}
]

for cat in CATS:
    try:
        resp = requests.get(cat["url"], headers=headers, timeout=10)
        print(f"{cat['name']}: {cat['url']} -> Status {resp.status_code}")
    except Exception as e:
        print(f"{cat['name']}: {cat['url']} -> Error {e}")
