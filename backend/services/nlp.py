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
    # Strictly traffic only keywords for title match
    "Trafik Kazası": ["trafik kazası", "zincirleme kaza", "şarampol", "takla attı"],
    "Yangın": ["yangın", "alev", "itfaiye", "kundaklama", "kül oldu", "yanarak", "duman"],
    "Elektrik Kesintisi": ["elektrik kesintisi", "trafo", "elektrikler kesilecek", "planlı kesinti", "sedaş", "karanlıkta kaldı"],
    "Hırsızlık": ["hırsız", "hırsızlık", "çalındı", "soygun", "gasp", "çaldı", "yankesici", "dolandırıcı"],
    "Kültürel Etkinlikler": ["kültürel", "etkinlik", "konser", "festival", "sergi", "tiyatro", "fuar", "kitap fuarı", "şenlik", "gösteri"]
}

# Crime/Police operation keywords that should NOT trigger other categories (they will fall into 'Diğer')
EXCLUSIONS = ["narkotik", "uyuşturucu", "silah", "ele geçirildi", "gözaltı", "operasyon", "sahte para", "asayiş"]

def classify_news(content, title=""):
    """
    Classifies news by searching for keywords.
    1. Checks the title first (most accurate).
    2. Checks content if title is inconclusive.
    Returns the highest priority matching category.
    """
    if not content and not title:
        return "Diğer"
        
    text_to_check = (title + " " + content).lower()
    title_lower = title.lower()
    
    # 0. Global Exclusions (If these are present, it's likely a police op/crime, so 'Diğer')
    for exc in EXCLUSIONS:
        if exc in text_to_check:
            return "Diğer"

    # 1. Quick check on title (Priority)
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', title_lower):
                return category

    # 2. Strict check on Traffic Accidents 
    # Must have both a generic accident keyword AND a vehicle keyword
    secondary_traffic = ["kaza", "çarpıştı", "devrildi", "yaralandı", "ölü", "can pazarı"]
    vehicle_keywords = ["araç", "otomobil", "kamyon", "tır", "motosiklet", "bisiklet", "minibüs", "servis", "otobüs"]

    has_vehicle = any(v in text_to_check for v in vehicle_keywords)
    has_secondary = any(sk in text_to_check for sk in secondary_traffic)

    if has_vehicle and has_secondary:
        return "Trafik Kazası"

    # 3. Check other categories in content
    for category, keywords in CATEGORIES.items():
        if category == "Trafik Kazası": continue 
        for keyword in keywords:
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_to_check):
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

