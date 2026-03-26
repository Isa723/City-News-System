import re

# Load multi-lingual embedding model to compare Turkish news similarity 
# As requested by the assignment for %90 similarity checking
# Loading lazily to prevent massive startup overhead if not used immediately
_model = None
_model_load_failed = False

def get_model():
    global _model, _model_load_failed
    if _model is None and not _model_load_failed:
        try:
            from sentence_transformers import SentenceTransformer
            import torch
            _model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        except Exception as e:
            print(f"Error loading SentenceTransformer: {e}")
            _model_load_failed = True
    return _model

# Semantic Category Definitions
CATEGORIES_SEMANTIC = {
    "Trafik Kazası": "trafik kazası çarpışma zincirleme kaza devrilen araç şarampol feci kaza ölümlü yaralamalı trafik kazası yol kapandı",
    "Yangın": "yangın alev bina yanması duman itfaiye müdahalesi orman yangını çatı yanması alevlere teslim itfaiye ekipleri",
    "Hırsızlık": "hırsızlık soygun gasp çalınma hırsız yakalandı ev soyuldu dükkan soygunu yankesicilik dolandırıcılık operasyon",
    "Elektrik Kesintisi": "elektrik kesintisi enerji yok karanlık trafo arızası ışıklar gitti planlı kesinti sedaş elektrikler yok arıza onarım",
    "Kültürel Etkinlikler": "festival konser etkinlik tiyatro kutlama sergi kitap fuarı şenlik kültür sanat müze sergisi gösteri"
}

# Crime/Police operation keywords that should always fall into 'Diğer'
POLICE_OP_EXCLUSIONS = ["narkotik", "uyuşturucu", "silah", "ele geçirildi", "gözaltı", "operasyon", "sahte para", "asayiş"]

# Municipal / Routine / Political keywords that incorrectly trigger categories
GENERAL_EXCLUSIONS = [
    "iftar", "davet", "başkan", "belediye", "hizmet", "proje", "ziyaret", 
    "açılış", "tören", "kutlama", "bayram", "meclis", "seçim", "parti", 
    "milletvekili", "valilik", "kaymakam", "program", "buluşma", "sofra",
    "hizmet binası", "temel atma", "denetim", "inceleme"
]

# Legal/Court process exclusions to prevent trials for old crimes being marked as active events
LEGAL_EXCLUSIONS = [
    "dava", "mahkeme", "sanık", "duruşma", "hakim", "savcı", "adliye", "avukat", 
    "yargılama", "hapis cezası", "müebbet", "tahliye", "beraat", "suç duyurusu"
]

# Global pre-computed embeddings for categories (Loaded lazily)
_category_embeddings = None

def get_category_embeddings():
    global _category_embeddings
    if _category_embeddings is None:
        model = get_model()
        if model:
            categories = list(CATEGORIES_SEMANTIC.keys())
            descriptions = [CATEGORIES_SEMANTIC[cat] for cat in categories]
            _category_embeddings = {
                "categories": categories,
                "embeddings": model.encode(descriptions, convert_to_tensor=True)
            }
    return _category_embeddings

def classify_news(content, title=""):
    """
    Classifies news by comparing content similarity with category descriptions (Semantic AI).
    """
    if not content and not title:
        return "Diğer"

    text_to_check = (title + " " + content[:400]).lower()
    
    # helper for exclusion check
    def has_exact(word_list, text):
        suffixes = r'(?:lar|ler)?(?:ı|i|u|ü|a|e|da|de|ta|te|ya|ye|na|ne|nın|nin|nun|nün|dan|den|tan|ten|sı|si|su|sü|yı|yi|yu|yü)?'
        for w in word_list:
            if ' ' in w: 
                if re.search(r'\b' + re.escape(w) + r'\b', text):
                    return True
            else:
                if re.search(r'\b' + re.escape(w) + suffixes + r'\b', text):
                    return True
        return False

    # Combined exclusions
    all_exclusions = [
        "narkotik", "uyuşturucu", "silah ele", "sahte para", "operasyon", "şüpheli", 
        "belediye başkanı", "meclis toplantısı", "milletvekili", 
        "antrenman", "turnuva", "müsabaka", "şampiyona", "spor", "idman", "kupa",
        "fenomen", "sosyal medya", "tutuklama", "gözaltı", "darbe", "yakalandı", 
        "ihraç", "terör", "firari", "cezaevi", "hapis", "emniyet", "polis"
    ] + GENERAL_EXCLUSIONS + LEGAL_EXCLUSIONS
    
    national_cities = [
        "adana", "ankara", "antalya", "aydın", "balıkesir", "bursa", "diyarbakır", 
        "erzurum", "eskişehir", "gaziantep", "hatay", "mersin", "istanbul", "izmir", 
        "kayseri", "konya", "malatya", "manisa", "kahramanmaraş", "mardin", "muğla", 
        "ordu", "samsun", "şanlıurfa", "tekirdağ", "trabzon", "van"
    ]
    
    if has_exact(all_exclusions, title.lower()) or has_exact(national_cities, title.lower()):
        # Exception for cultural events that might contain exclusion words
        if not has_exact(["konser", "festival", "tiyatro", "sergi"], title.lower()):
            return "Diğer"

    # 1. Follow-up / Retrospective Filtering (News about things that already happened)
    # E.g. "Yangında evi yanan çifte ev yapıldı" -> Not a 'Fire' event.
    follow_up_indicators = [
        "yeniden kuruldu", "ev yapıldı", "yardım eli", "ziyaret etti", "ziyaret", 
        "geçmiş olsun", "onarıldı", "yardım yapıldı", "destek verildi", "teslim edildi",
        "yıldönümü", "anıldı", "anma"
    ]
    if has_exact(follow_up_indicators, text_to_check):
        return "Diğer"

    # AI-based Semantic Categorization
    model = get_model()
    cat_data = get_category_embeddings()
    
    if model and cat_data:
        try:
            from sentence_transformers import util
            text_emb = model.encode(text_to_check, convert_to_tensor=True)
            scores = util.cos_sim(text_emb, cat_data["embeddings"])[0]
            
            max_idx = int(scores.argmax().item())
            max_score = float(scores[max_idx].item())
            
            # Confidence Threshold for categorization
            # Stricter thresholds based on user feedback
            threshold = 0.35 
            if cat_data["categories"][max_idx] == "Trafik Kazası":
                threshold = 0.45
            elif cat_data["categories"][max_idx] == "Hırsızlık":
                threshold = 0.40 # Higher threshold to avoid false positives like court cases
            
            if max_score > threshold:
                return cat_data["categories"][max_idx]
        except Exception as e:
            print(f"Semantic classification failed: {e}")

    return "Diğer"

    return "Diğer"

def check_similarity(text1, text2):
    """
    Returns the similarity score between two texts using multilingual embeddings.
    Returns a float between 0.0 and 1.0
    """
    try:
        from sentence_transformers import util
    except ImportError:
        return 0.0

    model = get_model()
    if not model or not text1 or not text2:
        return 0.0
        
    embeddings1 = model.encode(text1, convert_to_tensor=True)
    embeddings2 = model.encode(text2, convert_to_tensor=True)
    
    # Compute cosine similarity
    cosine_scores = util.cos_sim(embeddings1, embeddings2)
    
    return cosine_scores[0][0].item()

def is_duplicate(new_text, existing_items, threshold=0.90):
    """
    Checks if a new_text is at least 90% similar to ANY existing text.
    """
    if not existing_items:
        return False, 0.0, None
        
    legacy_mode = isinstance(existing_items[0], str)

    # Legacy slow path kept for safety.
    if legacy_mode:
        max_score = 0.0
        matched = None
        for ext_text in existing_items:
            if not ext_text:
                continue
            score = check_similarity(new_text, ext_text)
            if score > max_score:
                max_score = score
                matched = ext_text
        if max_score >= threshold:
            return True, max_score, matched
        return False, max_score, None

    # Optimized path: compute embeddings once, compare in batch.
    model = get_model()
    if not model or not new_text:
        return False, 0.0, None

    try:
        from sentence_transformers import util
    except Exception:
        return False, 0.0, None

    ext_texts: list[str] = []
    ext_ids: list = []
    for item in existing_items:
        if not item:
            continue
        ext_text = item.get("content") or ""
        if not ext_text:
            continue
        ext_texts.append(ext_text)
        ext_ids.append(item.get("_id"))

    if not ext_texts:
        return False, 0.0, None

    # Batch encoding massively reduces runtime vs per-item similarity.
    new_emb = model.encode(new_text, convert_to_tensor=True)
    existing_emb = model.encode(ext_texts, convert_to_tensor=True)
    scores = util.cos_sim(new_emb, existing_emb)[0]

    max_idx = int(scores.argmax().item())
    max_score = float(scores[max_idx].item())
    matched_id = ext_ids[max_idx]

    if max_score >= threshold:
        return True, max_score, matched_id
    return False, max_score, None
