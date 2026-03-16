from sentence_transformers import SentenceTransformer, util
import torch
import re

# Load multi-lingual embedding model to compare Turkish news similarity 
# As requested by the assignment for %90 similarity checking
# Loading lazily to prevent massive startup overhead if not used immediately
try:
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
except Exception as e:
    print(f"Error loading SentenceTransformer: {e}")
    model = None

# PDF Category Definitions and Keywords (Priority order: top to bottom)
CATEGORIES = {
    "Trafik Kazası": ["trafik kazası", "zincirleme kaza", "şarampol", "takla attı", "otomobil devrildi", "feci kaza"],
    "Yangın": ["yangın çıktı", "alevlere teslim", "itfaiye müdahale", "ev yandı", "fabrika yangını", "orman yangını", "çatıda yangın"],
    "Elektrik Kesintisi": ["elektrik kesintisi", "planlı kesinti", "sedaş", "trafo patladı", "elektrikler kesilecek"],
    "Hırsızlık": ["hırsızlık", "çalındı", "soygun", "gasp", "çaldı", "yankesici"],
    "Kültürel Etkinlikler": ["konser", "festival", "tiyatro", "sergi", "kitap fuarı", "şenlik", "gösteri", "sinema", "kültür sanat"]
}

# Crime/Police operation keywords that should always fall into 'Diğer'
POLICE_OP_EXCLUSIONS = ["narkotik", "uyuşturucu", "silah", "ele geçirildi", "gözaltı", "operasyon", "sahte para", "asayiş"]

# Municipal / Routine / Political keywords that incorrectly trigger categories
# E.g. "Başkan iftar davet" should NOT be a "Trafik Kazası" just because it mentions a "street"
GENERAL_EXCLUSIONS = [
    "iftar", "davet", "başkan", "belediye", "hizmet", "proje", "ziyaret", 
    "açılış", "tören", "kutlama", "bayram", "meclis", "seçim", "parti", 
    "milletvekili", "valilik", "kaymakam", "program", "buluşma", "sofra"
]

def classify_news(content, title=""):
    """
    Classifies news by searching for keywords with strict verification.
    """
    if not content and not title:
        return "Diğer"
        
    text_to_check = (title + " " + content).lower()
    title_lower = title.lower()
    
    # 0. Global Exclusions (Police & General)
    # If it's a routine city news or a crime report, it's 'Diğer'
    all_exclusions = POLICE_OP_EXCLUSIONS + GENERAL_EXCLUSIONS
    for exc in all_exclusions:
        if exc in title_lower: # If it's in the title, it's almost certainly NOT a critical event
            return "Diğer"

    # 1. Traffic Accident - Strict 2-Factor Verification
    # Requirement: Must have an explicit accident word AND a vehicle
    # Must NOT have traffic 'regulation' or 'limit' keywords
    traffic_negatives = ["hız limiti", "tabela", "radar", "eds", "denetim", "ceza", "otopark", "park yasağı"]
    if not any(tn in text_to_check for tn in traffic_negatives):
        accident_keywords = ["kaza", "çarpıştı", "devrildi", "yaralandı", "ölü", "can pazarı", "takla", "şarampol"]
        vehicle_keywords = ["araç", "otomobil", "kamyon", "tır", "motosiklet", "bisiklet", "minibüs", "otobüs"]
        
        has_accident = any(ak in text_to_check for ak in accident_keywords)
        has_vehicle = any(vk in text_to_check for vk in vehicle_keywords)
        
        if has_accident and has_vehicle:
            # Final check: If it's just a 'limit' or 'parking' news, it might still have these words
            if not any(exc in title_lower for exc in ["otopark", "limit", "tabela"]):
                return "Trafik Kazası"

    # 2. Yangın - Refined
    fire_keywords = ["yangın", "alev", "itfaiye", "yanarak", "kül oldu"]
    if any(fk in title_lower for fk in fire_keywords):
        return "Yangın"

    # 3. Check other categories (Hırsızlık, Elektrik, Kültürel)
    # Give priority to category keywords in Title
    for category, keywords in CATEGORIES.items():
        if category == "Trafik Kazası": continue
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', title_lower):
                return category

    # 4. Check Content as fallback (but be stricter)
    for category, keywords in CATEGORIES.items():
        if category == "Trafik Kazası": continue
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_to_check):
                # Ensure it's not a false positive for Fire (e.g. gas leak without fire)
                if category == "Yangın" and "gaz sızıntısı" in text_to_check and "yangın" not in title_lower:
                    continue
                return category
                
    return "Diğer"

def check_similarity(text1, text2):
    """
    Returns the similarity score between two texts using multilingual embeddings.
    Returns a float between 0.0 and 1.0
    """
    if not model or not text1 or not text2:
        return 0.0
        
    embeddings1 = model.encode(text1, convert_to_tensor=True)
    embeddings2 = model.encode(text2, convert_to_tensor=True)
    
    # Compute cosine similarity
    cosine_scores = util.cos_sim(embeddings1, embeddings2)
    
    return cosine_scores[0][0].item()

def is_duplicate(new_text, existing_texts, threshold=0.90):
    """
    Checks if a new_text is at least 90% similar to ANY existing text.
    Returns (True, max_score, matched_text) if it is a duplicate.
    """
    if not existing_texts:
        return False, 0.0, None
        
    max_score = 0.0
    matched_text = None
    for ext in existing_texts:
        score = check_similarity(new_text, ext)
        if score > max_score:
            max_score = score
            matched_text = ext
            
    if max_score >= threshold:
        return True, max_score, matched_text
    return False, max_score, None

