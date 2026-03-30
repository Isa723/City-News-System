import requests

tests = [
    "https://www.cagdaskocaeli.com.tr/gundem/",
    "https://www.ozgurkocaeli.com.tr/gundem/",
    "https://www.seskocaeli.com/guncel/",
    "https://www.yenikocaeli.com/gundem/",
    "https://www.bizimyaka.com/gundem/"
]

headers = {"User-Agent": "Mozilla/5.0"}

print("Final Diagnostic: Simple requests on category pages...")

for url in tests:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"URL: {url} -> Status: {r.status_code}, Length: {len(r.text)}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
