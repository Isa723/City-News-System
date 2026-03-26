import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Handle Turkish characters on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from backend.services.nlp import classify_news
from backend.services.geocoding import extract_location_info

def test_semantic_classification():
    print("--- Testing Semantic Classification ---")
    test_cases = [
        ("mahalle günlerdir ışıksız kaldı", "Elektrik Kesintisi"),
        ("D-100 karayolunda iki araç kafa kafaya vuruştu", "Trafik Kazası"),
        ("Binadaki alevler gökyüzünü sardı", "Yangın"),
        ("Evdeki mücevherleri çalıp kayıplara karıştılar", "Hırsızlık"),
        ("Kocaeli'de Şehir Tiyatroları muhteşem bir prömiyer yaptı", "Kültürel Etkinlikler"),
        ("Belediye başkanı park açılışına katıldı", "Diğer"),
        ("Atığını sokağa atan sürücüye fotokapan takibi", "Diğer"), # Should NOT be Trafik Kazası
        ("Yangında evleri küle dönmüştü: Aktekin çiftinin sıcak yuvası yeniden kuruldu.", "Diğer"), # Retrospective
        ("Dilovası’nda hayvan ağılında yangın!", "Yangın")
    ]
    
    for text, expected in test_cases:
        result = classify_news(text, title="")
        status = "✅" if result == expected else f"❌ (Got: {result})"
        print(f"Text: '{text}' -> Result: {result} {status}")

def test_ner_location_extraction():
    print("\n--- Testing NER Location Extraction ---")
    test_cases = [
        ("Gebze mahallesinde yangın çıktı.", "Gebze"),
        ("İzmit Yürüyüş Yolu üzerinde etkinlik düzenlendi.", "İzmit"),
        ("Körfez Tütünçiftlik mevkiinde kaza.", "Körfez"),
        ("Kartepe'de kar yağışı durdu.", "Kartepe")
    ]
    
    for text, expected in test_cases:
        # We pass empty title or same text for simplicity in test
        result = extract_location_info("", text)
        if result:
            best = result.get("best_location_text", "None")
            district = result.get("district", "None")
            print(f"Text: '{text}' -> Best Location: {best}, District: {district}")
        else:
            print(f"Text: '{text}' -> No location found ❌")

if __name__ == "__main__":
    test_semantic_classification()
    test_ner_location_extraction()
