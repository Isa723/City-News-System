import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from services.nlp import classify_news

def test_nlp():
    test_cases = [
        {
            "title": "Büyükşehir den Dilovası na modern hizmet binası",
            "content": "Kocaeli Büyükşehir Belediyesi Dilovası ilçesine modern bir hizmet binası kazandırıyor.",
            "expected": "Diğer"
        },
        {
            "title": "Dilovası davasında sanığın Şov yapmayın sözleri tansiyonu yükseltti",
            "content": "Kocaeli Dilovası'ndaki bir davanın duruşmasında sanığın hakime yönelik sözleri ortalığı karıştırdı.",
            "expected": "Diğer"
        },
        {
            "title": "Körfez'de trafik kazası: 2 yaralı",
            "content": "Kocaeli'nin Körfez ilçesinde iki otomobilin çarpışması sonucu meydana gelen trafik kazasında 2 kişi yaralandı.",
            "expected": "Trafik Kazası"
        }
    ]

    print("--- NLP Fix Verification ---")
    for tc in test_cases:
        result = classify_news(tc["content"], tc["title"])
        status = "✅ PASS" if result == tc["expected"] else f"❌ FAIL (Got: {result})"
        print(f"Title: {tc['title'][:50]}...")
        print(f"Result: {result} | Expected: {tc['expected']} | {status}")
        print("-" * 30)

if __name__ == "__main__":
    test_nlp()
