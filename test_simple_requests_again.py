import requests

SITES = [
    "https://www.cagdaskocaeli.com.tr/",
    "https://www.ozgurkocaeli.com.tr/",
    "https://www.seskocaeli.com/",
    "https://www.yenikocaeli.com/",
    "https://www.bizimyaka.com/"
]

headers = {"User-Agent": "Mozilla/5.0"}

for site in SITES:
    try:
        response = requests.get(site, headers=headers, timeout=10)
        print(f"{site}: Status {response.status_code}, Length {len(response.text)}")
    except Exception as e:
        print(f"{site}: Error {e}")
