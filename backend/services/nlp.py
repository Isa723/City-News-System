from __future__ import annotations

from services.geocoding import _mentions_other_turkey_place

# --- SentenceTransformer: duplicate detection (%90 similarity), unchanged ---
_model = None
_model_load_failed = False


def get_model():
    global _model, _model_load_failed
    if _model is None and not _model_load_failed:
        try:
            from sentence_transformers import SentenceTransformer

            _model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        except Exception as e:
            print(f"Error loading SentenceTransformer: {e}")
            _model_load_failed = True
    return _model


# --- mDeBERTa zero-shot: categorization only (lazy load) ---
_classifier = None
_classifier_failed = False


def _contains_any(text: str, keywords: list[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def _has_category_evidence(label: str, text: str) -> bool:
    t = (text or "").lower()
    evidence = {
        "Trafik Kazası": [
            "kaza", "trafik", "çarp", "çarpış", "zincirleme", "devril", "takla", "sürücü", "araç",
        ],
        "Yangın": [
            "yangın", "alev", "duman", "itfaiye", "yandı", "yanan", "yanarak", "küller", "kule döndü",
        ],
        "Hırsızlık": [
            "hırsız", "hırsızlık", "soygun", "gasp", "çal", "yağma", "kasadan", "çalındı",
        ],
        "Elektrik Kesintisi": [
            "elektrik kesint", "elektrikler kesildi", "enerji kesint", "sedaş", "sedaş", "trafo", "arıza",
        ],
        "Kültürel Etkinlikler": [
            "festival", "konser", "tiyatro", "etkinlik", "sergi", "şenlik", "gösteri", "sahne",
        ],
    }
    return _contains_any(t, evidence.get(label, []))


def get_classifier():
    global _classifier, _classifier_failed
    if _classifier is not None or _classifier_failed:
        return _classifier
    try:
        import torch
        from transformers import pipeline

        print("Loading mDeBERTa zero-shot classifier (MoritzLaurer/mDeBERTa-v3-base-mnli-xnli)...")
        use_cuda = torch.cuda.is_available()
        if use_cuda:
            _classifier = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                device=0,
                torch_dtype=torch.float16,
            )
        else:
            _classifier = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                device=-1,
            )
    except Exception as e:
        print(f"Zero-shot classifier load failed: {e}")
        _classifier_failed = True
        _classifier = None
    return _classifier


def classify_news(content, title=""):
    """
    Zero-shot labels + trap categories (court, politics, sports, …) → single best label.
    """
    if not content and not title:
        return "Diğer"

    if _mentions_other_turkey_place(title, (content or "")[:1200]):
        return "Diğer"

    text_to_check = f"{title}. {(content or '')[:600]}"

    candidate_labels = [
        "Trafik Kazası",
        "Yangın",
        "Hırsızlık",
        "Elektrik Kesintisi",
        "Kültürel Etkinlik",
        "Cinayet ve Şiddet",
        "Asayiş ve Polis Operasyonu",
        "Mahkeme ve Adliye",
        "Siyaset ve Belediye",
        "Spor",
        "Ekonomi ve İş",
        "Eğitim",
    ]

    hypothesis_template = "Bu haber {} hakkındadır."

    classifier = get_classifier()
    if classifier is None:
        return "Diğer"

    try:
        result = classifier(
            text_to_check,
            candidate_labels,
            hypothesis_template=hypothesis_template,
            multi_label=False,
        )

        best_label = result["labels"][0]
        best_score = float(result["scores"][0])

        print(f"   AI: {best_label} ({best_score * 100:.1f}%)")

        if best_label == "Kültürel Etkinlik":
            best_label = "Kültürel Etkinlikler"

        target_categories = [
            "Trafik Kazası",
            "Yangın",
            "Hırsızlık",
            "Elektrik Kesintisi",
            "Kültürel Etkinlikler",
        ]

        # Hard gate: never emit rubric category without lexical evidence.
        if best_label in target_categories and not _has_category_evidence(best_label, text_to_check):
            return "Diğer"

        if best_label in target_categories and best_score > 0.35:
            return best_label
        return "Diğer"
    except Exception as e:
        print(f"Classification failed: {e}")
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

    cosine_scores = util.cos_sim(embeddings1, embeddings2)

    return cosine_scores[0][0].item()


def is_duplicate(new_text, existing_items, threshold=0.90):
    """
    Checks if a new_text is at least 90% similar to ANY existing text.
    """
    if not existing_items:
        return False, 0.0, None

    legacy_mode = isinstance(existing_items[0], str)

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

    new_emb = model.encode(new_text, convert_to_tensor=True)
    existing_emb = model.encode(ext_texts, convert_to_tensor=True)
    scores = util.cos_sim(new_emb, existing_emb)[0]

    max_idx = int(scores.argmax().item())
    max_score = float(scores[max_idx].item())
    matched_id = ext_ids[max_idx]

    if max_score >= threshold:
        return True, max_score, matched_id
    return False, max_score, None
