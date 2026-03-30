import requests

sites = [
    "https://www.yenikocaeli.com/kategori/gundem/",
    "https://www.yenikocaeli.com/kategori/son-dakika/",
    "https://www.bizimyaka.com/kategori/gundem/",
    "https://www.bizimyaka.com/haberler/"
]

headers = {"User-Agent": "Mozilla/5.0"}

for url in sites:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url} -> Status: {r.status_code}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
