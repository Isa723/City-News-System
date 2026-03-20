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

# PDF Category Definitions and Keywords (Priority order: top to bottom)
CATEGORIES = {
    "Trafik Kazası": ["trafik kazası", "zincirleme kaza", "şarampol", "takla attı", "otomobil devrildi", "feci kaza"],
    "Yangın": ["yangın çıktı", "alevlere teslim", "itfaiye müdahale", "ev yandı", "fabrika yangını", "orman yangını", "çatıda yangın", "yangın"],
    "Elektrik Kesintisi": ["elektrik kesintisi", "planlı kesinti", "sedaş", "trafo patladı", "elektrikler kesilecek"],
    "Hırsızlık": ["hırsızlık", "çalındı", "soygun", "gasp", "çaldı", "yankesici"],
    "Kültürel Etkinlikler": ["konser", "festival", "tiyatro", "sergi", "kitap fuarı", "şenlik", "gösteri", "sinema", "kültür sanat"],
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
    Classifies news by searching for strict keyword boundaries to prevent false positives.
    """
    if not content and not title:
        return "Diğer"

    text_to_check = (title + " " + content).lower()
    title_lower = title.lower()

    # Helper: checks if ANY of the exact words/phrases are in the text
    def has_exact(word_list, text):
        for w in word_list:
            if re.search(r'\b' + re.escape(w) + r'\b', text):
                return True
        return False

    # 0. Global Exclusions (Crime operations, sports, irrelevant daily events)
    exclusions = [
        "narkotik", "uyuşturucu", "silah ele", "sahte para", "operasyon", "şüpheli", 
        "iftar", "davet", "belediye başkanı", "ziyaret", "açılış", "tören", 
        "kutlama", "bayram", "meclis toplantısı", "milletvekili", 
        "antrenman", "turnuva", "müsabaka", "şampiyona", "spor", "idman", "kupa"
    ]
    # If the title heavily implies a police op or a sport event, skip immediately (unless it's a cultural event)
    if has_exact(exclusions, title_lower):
        # We only let it pass if it's explicitly explicitly a cultural event 
        if not has_exact(["konser", "festival", "tiyatro", "sergi"], title_lower):
            return "Diğer"

    # 1. Trafik Kazası
    traffic_exact = ["trafik kazası", "zincirleme", "şarampol", "takla attı", "feci kaza", "araç takla"]
    if has_exact(traffic_exact, text_to_check):
        return "Trafik Kazası"
        
    kaza_words = ["kaza", "kazası", "kazada", "kazaya", "çarpıştı", "devrildi", "yaya çarp"]
    vehicle_words = ["araç", "aracı", "araçlar", "araçta", "otomobil", "kamyon", "tır", "motosiklet", "bisiklet", "minibüs", "otobüs"]
    
    if has_exact(kaza_words, text_to_check) and has_exact(vehicle_words, text_to_check):
        if not has_exact(["iş kazası", "görünmez kaza", "iş cinayeti"], text_to_check):
            return "Trafik Kazası"

    # 2. Yangın
    fire_words = ["yangın", "yangını", "yangında", "yangına", "alevlere teslim", "itfaiye", "itfaiyesi", "kül oldu", "kundaklama", "kundaklandı"]
    if has_exact(fire_words, title_lower):
        return "Yangın"
    if has_exact(fire_words, text_to_check):
        # Prevent false positives like 'orman yangını tatbikatı' or someone whose name is Alev 
        if not has_exact(["tatbikat", "tatbikatı", "film", "dizi"], text_to_check):
            return "Yangın"

    # 3. Diğer Kategoriler (Elektrik, Hırsızlık, Kültürel Etkinlikler)
    OTHER_CATEGORIES = {
        "Elektrik Kesintisi": [
            "elektrik kesintisi", "planlı kesinti", "sedaş", "trafo patladı", "elektrikler kesilecek", "elektrik kesilecek", "elektrik arızası"
        ],
        "Hırsızlık": [
            "hırsızlık", "soygun", "gasp", "yankesici", "hırsız", "kuyumcu soygunu", "çalındı", "çaldı"
        ],
        "Kültürel Etkinlikler": [
            "konser", "festival", "tiyatro", "sergi", "kitap fuarı", "şenlik", "gösteri", "sinema", "kültür sanat", "etkinlik", "söyleşi"
        ]
    }

    # Title match gets priority
    for category, keywords in OTHER_CATEGORIES.items():
        if has_exact(keywords, title_lower):
            return category

    # Body match
    for category, keywords in OTHER_CATEGORIES.items():
        if has_exact(keywords, text_to_check):
            return category

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
    existing_items can be either:
    - list[str] (legacy)
    - list[dict] containing {"_id": ..., "content": "..."}
    Returns (True, max_score, matched) where matched is either the matched text (legacy)
    or the matched document _id (preferred).
    """
    if not existing_items:
        return False, 0.0, None
        
    max_score = 0.0
    matched = None

    legacy_mode = isinstance(existing_items[0], str)

    for item in existing_items:
        if legacy_mode:
            ext_text = item
            ext_id = None
        else:
            ext_text = item.get("content") or ""
            ext_id = item.get("_id")

        if not ext_text:
            continue

        score = check_similarity(new_text, ext_text)
        if score > max_score:
            max_score = score
            matched = ext_text if legacy_mode else ext_id
            
    if max_score >= threshold:
        return True, max_score, matched
    return False, max_score, None

