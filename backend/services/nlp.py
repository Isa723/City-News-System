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
    "Trafik Kazası": ["trafik kazası", "kaza", "çarpıştı", "devrildi", "şarampol", "yaralandı", "karayolu kaza", "zincirleme kaza"],
    "Yangın": ["yangın", "alev", "itfaiye", "kundaklama", "kül oldu", "yanarak", "duman"],
    "Elektrik Kesintisi": ["elektrik kesintisi", "trafo", "elektrikler kesilecek", "planlı kesinti", "sedaş", "karanlıkta kaldı"],
    "Hırsızlık": ["hırsız", "hırsızlık", "çalındı", "soygun", "gasp", "çaldı", "yankesici", "dolandırıcı"],
    "Kültürel Etkinlikler": ["kültürel", "etkinlik", "konser", "festival", "sergi", "tiyatro", "fuar", "kitap fuarı", "şenlik", "gösteri"]
}

def classify_news(text):
    """
    Classifies news by searching for keywords in the text.
    Returns the highest priority matching category.
    If multiple match, the first defined in the dictionary takes precedence.
    If none match, returns 'Diğer' (Other).
    """
    if not text:
        return "Diğer"
        
    text_lower = text.lower()
    
    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            # Word boundary regex to ensure exact match of the phrase/word
            if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
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
    Returns True if it is a duplicate, along with the max similarity score.
    """
    if not existing_texts:
        return False, 0.0
        
    max_score = 0.0
    for ext in existing_texts:
        score = check_similarity(new_text, ext)
        if score > max_score:
            max_score = score
            
    if max_score >= threshold:
        return True, max_score
    return False, max_score

