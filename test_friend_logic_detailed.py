import requests

sites_to_test = [
    # Cagdas
    "https://www.cagdaskocaeli.com.tr/gundem/",
    "https://www.cagdaskocaeli.com.tr/arsiv/",
    # Ozgur
    "https://www.ozgurkocaeli.com.tr/gundem/",
    "https://www.ozgurkocaeli.com.tr/arsiv/",
    # Ses
    "https://www.seskocaeli.com/guncel/",
    "https://www.seskocaeli.com/arsiv/",
    # Yeni
    "https://www.yenikocaeli.com/gundem/",
    "https://www.yenikocaeli.com/arsiv/",
    # Bizim Yaka
    "https://www.bizimyaka.com/gundem/",
    "https://www.bizimyaka.com/arsiv/"
]

headers = {"User-Agent": "Mozilla/5.0"}

print("Starting Simple Request Test (Friend's logic)...")

for url in sites_to_test:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url} -> Status: {r.status_code}")
        if r.status_code == 200:
            print(f"   [SUCCESS] Length: {len(r.text)}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
