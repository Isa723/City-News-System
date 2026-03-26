import sys
import os
import io

# Set UTF-8 encoding for stdout
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to sys.path
sys.path.append(r"C:\Users\PISHTAAZ SOFTWARE\Desktop\Project")

from backend.services.nlp import classify_news

test_cases = [
    ("Atığını sokağa atan sürücüye fotokapan takibi", "Diğer"),
    ("Yangında evleri küle dönmüştü: Aktekin çiftinin sıcak yuvası yeniden kuruldu.", "Diğer"),
    ("Dilovası’nda hayvan ağılında yangın!", "Yangın")
]

print("--- RESULTS ---")
for text, expected in test_cases:
    result = classify_news(text, title="")
    print(f"CASE: '{text}'")
    print(f"EXPECTED: {expected} | GOT: {result}")
    print("MATCH: " + ("PASS" if result == expected else "FAIL"))
    print("-" * 20)
