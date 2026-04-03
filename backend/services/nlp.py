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
TARGET_LABELS = [
    "Trafik Kazası",
    "Yangın",
    "Hırsızlık",
    "Elektrik Kesintisi",
    "Kültürel Etkinlik",
]
TRAP_LABELS = [
    "Cinayet ve Şiddet",
    "Asayiş ve Polis Operasyonu",
    "Mahkeme ve Adliye",
    "Siyaset ve Belediye",
    "Spor",
    "Ekonomi ve İş",
    "Eğitim",
    "Sağlık",
    "Magazin",
]
RELEVANCE_LABELS = [
    "Kocaeli yerel olay haberi",
    "Kocaeli dışı haber",
    "Olay içermeyen duyuru veya genel haber",
]


def _contains_any(text: str, keywords: list[str]) -> bool:
    t = (text or "").lower()
    return any(k in t for k in keywords)


def _category_score(label: str, text: str) -> float:
    t = (text or "").lower()
    evidence_weights = {
        "Trafik Kazası": [
            ("trafik kazası", 3.0),
            ("zincirleme", 2.5),
            ("çarpış", 2.0),
            ("çarp", 1.5),
            ("kaza", 2.8),
            ("devril", 2.0),
            ("takla", 2.0),
            ("yaralı", 1.3),
            ("sürücü", 1.0),
            ("araç", 0.8),
            ("trafik", 0.5),
        ],
        "Yangın": [
            ("yangın", 3.0),
            ("alev", 2.0),
            ("itfaiye", 2.0),
            ("küle döndü", 3.0),
            ("duman", 1.5),
            ("yandı", 2.2),
            ("yanan", 1.8),
            ("yanarak", 1.8),
            ("alev aldı", 2.5),
            ("yangın çıktı", 2.5),
        ],
        "Hırsızlık": [
            ("hırsızlık", 3.0),
            ("hırsız", 2.8),
            ("soygun", 2.6),
            ("gasp", 2.6),
            ("yağma", 2.8),
            ("çalındı", 2.5),
            ("çal", 1.2),
            ("kasadan", 1.8),
        ],
        "Elektrik Kesintisi": [
            ("elektrik kesint", 3.0),
            ("elektrikler kesildi", 3.0),
            ("enerji kesint", 2.8),
            ("sedaş", 2.4),
            ("trafo", 1.6),
            ("elektrik arıza", 2.0),
            ("enerji verilemedi", 2.2),
            ("elektriksiz", 3.0),
        ],
        "Kültürel Etkinlikler": [
            ("festival", 2.8),
            ("konser", 2.8),
            ("tiyatro", 2.8),
            ("sergi", 2.4),
            ("şenlik", 2.2),
            ("gösteri", 2.0),
            ("sahne", 1.4),
            ("etkinlik", 1.0),
            ("kültür", 1.0),
        ],
    }
    score = 0.0
    for term, weight in evidence_weights.get(label, []):
        if term in t:
            score += weight

    # Strong blockers as penalty
    if _has_category_blocker(label, t):
        score -= 2.5

    # Event trigger requirement for critical categories
    triggers = {
        "Trafik Kazası": ["çarp", "çarpış", "devril", "takla", "kaza yaptı", "kaza"],
        "Yangın": ["yandı", "alev aldı", "yangın çıktı", "itfaiye müdahale", "alev"],
        "Hırsızlık": ["çalındı", "soygun", "gasp", "hırsızlık", "yağma"],
    }
    if label in triggers and not _contains_any(t, triggers[label]):
        score *= 0.5

    return score


def _has_category_blocker(label: str, text: str) -> bool:
    t = (text or "").lower()
    blockers = {
        "Yangın": [
            "ruhsat denetim", "bahar temizliği", "yabani ot",
            "ot biç", "ilaçlama", "denetimleri sürüyor",
            "yangın tatbikatı", "yangın eğitimi", "önlem",
            "yangın riski", "yangın uyarısı", "yangın önleme",
        ],

        "Elektrik Kesintisi": [
            "su kesintisi", "sular ne zaman", "isu'dan", "isu ",
            "su arızası", "su arizasi", "içme suyu", "kanalizasyon",
            "altyapı çalışması", "boru patladı", "su hattı",
        ],

        "Trafik Kazası": [
            "trafik denetimi", "trafik cezası", "ehliyet",
            "radar uygulaması", "kontrol noktası", "trafik eğitimi", 
            "trafik haftası", "ulaşım planı", "altyapı çalışması",
        ],

        "Hırsızlık": [
            "tatbikat", "film", "dizi", "senaryo",
        ],

        "Kültürel Etkinlikler": [
            "siyasi toplantı", "basın açıklaması",
            "protesto", "miting",
        ],
    }
    return _contains_any(t, blockers.get(label, []))


def _normalize_target_label(label: str) -> str:
    if label == "Kültürel Etkinlik":
        return "Kültürel Etkinlikler"
    return label


def _passes_relevance_gate(classifier, text_to_check: str) -> bool:
    try:
        result = classifier(
            text_to_check,
            RELEVANCE_LABELS,
            hypothesis_template="Bu metin {}.",
            multi_label=False,
        )
        top = result["labels"][0]
        score = float(result["scores"][0])
        # Be less aggressive: we only want to drop clearly non-local items.
        # Loosening prevents "important-but-unfamiliar" wording from being abstained too often.
        if top != "Kocaeli yerel olay haberi" and score >= 0.65:
            return False
        return True
    except Exception:
        # Technical error on gate should not hard-drop all news.
        return True


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
            # HF model card: mDeBERTa has known FP16 issues; use default float32 on GPU.
            name = torch.cuda.get_device_name(0)
            print(f"Zero-shot classifier device: CUDA (GPU 0: {name})")
            _classifier = pipeline(
                "zero-shot-classification",
                model="MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
                device=0,
            )
        else:
            print(
                "Zero-shot classifier device: CPU. "
                "torch.cuda.is_available() is False — usually CPU-only PyTorch, "
                "missing NVIDIA driver, or no CUDA-capable GPU. "
                "Install CUDA-enabled torch from https://pytorch.org/get-started/locally/ if you have an NVIDIA GPU."
            )
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
    candidate_labels = TARGET_LABELS + TRAP_LABELS

    hypothesis_template = "Bu haber {} hakkındadır."

    classifier = get_classifier()
    if classifier is None:
        return "Diğer"

    try:
        if not _passes_relevance_gate(classifier, text_to_check):
            return "Diğer"

        result = classifier(
            text_to_check,
            candidate_labels,
            hypothesis_template=hypothesis_template,
            multi_label=False,
        )
        score_map = {lab: float(sc) for lab, sc in zip(result["labels"], result["scores"])}
        best_target_raw = max(TARGET_LABELS, key=lambda l: score_map.get(l, 0.0))
        best_target = _normalize_target_label(best_target_raw)
        best_target_score = score_map.get(best_target_raw, 0.0)
        best_trap = max(TRAP_LABELS, key=lambda l: score_map.get(l, 0.0))
        best_trap_score = score_map.get(best_trap, 0.0)

        print(
            f"   AI target: {best_target} ({best_target_score * 100:.1f}%), "
            f"trap: {best_trap} ({best_trap_score * 100:.1f}%)"
        )

        # Trap ratio rule: if trap is too close/high, abstain.
        # Loosen a bit to prioritize recall over precision (user says missing is worse).
        if best_trap_score > (best_target_score * 0.90):
            return "Diğer"

        # Fuse AI score + weighted keyword score (title is boosted).
        fused_scores: dict[str, float] = {}
        for raw_label in TARGET_LABELS:
            norm_label = _normalize_target_label(raw_label)
            ai = score_map.get(raw_label, 0.0)
            kw_content = _category_score(norm_label, content or "")
            kw_title = _category_score(norm_label, title or "")
            kw_total = kw_content + (kw_title * 1.3)
            # Normalize keyword score to [0, 1] for stable fusion.
            kw_norm = max(0.0, min(1.0, kw_total / 10.0))
            fused_scores[norm_label] = (ai * 0.6) + (kw_norm * 0.4)

        best_fused = max(fused_scores, key=fused_scores.get)
        best_fused_score = fused_scores[best_fused]

        print(f"   FUSED: {best_fused} ({best_fused_score * 100:.1f}%)")

        # Minimum acceptance threshold.
        # Lowering slightly increases recall without adding more model calls.
        if best_fused_score < 0.45:
            return "Diğer"
        if _has_category_blocker(best_fused, text_to_check):
            return "Diğer"

        return best_fused
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
