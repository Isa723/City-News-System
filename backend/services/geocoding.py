from __future__ import annotations

import asyncio
import googlemaps
import os
import re
# import stanza  # Moved to lazy loading in get_stanza_nlp to prevent top-level ModuleNotFoundError
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorDatabase

# Load environment variables
load_dotenv()

# Initialize Google Maps Client
# Mandatory Requirement (Section 7): "API anahtarı güvenli biçimde saklanmalıdır."
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
_gmaps_client = None


def get_gmaps_client():
    global _gmaps_client
    if _gmaps_client is not None:
        return _gmaps_client
    if not API_KEY:
        return None
    try:
        _gmaps_client = googlemaps.Client(key=API_KEY)
        return _gmaps_client
    except Exception as e:
        print(f"Google Maps client init failed: {e}")
        return None

# Global Stanza Pipeline (Loaded lazily to save memory/startup time)
_stanza_nlp = None

def get_stanza_nlp():
    global _stanza_nlp
    if _stanza_nlp is None:
        try:
            import stanza
            # Only load 'tokenize' and 'ner' processors for speed
            _stanza_nlp = stanza.Pipeline("tr", processors='tokenize,ner', download_method=None)
        except (ImportError, Exception) as e:
            print(f"Stanza initialization failed or module not found: {e}")
    return _stanza_nlp

def _cache_key(location_name: str) -> str:
    return re.sub(r"\s+", " ", (location_name or "").strip().lower())

# List of Kocaeli Districts to extract from text
KOCAELI_DISTRICTS = [
    "İzmit", "Gebze", "Gölcük", "Derince", "Darıca", 
    "Körfez", "Kartepe", "Başiskele", "Karamürsel", 
    "Kandıra", "Dilovası", "Çayırova"
]

# Provinces / major cities outside Kocaeli (ASCII-folded keys; see _fold_tr).
OTHER_TURKEY_PLACES = frozenset(
    {
        "batman", "diyarbakir", "mardin", "sirnak", "hakkari", "van", "mus", "bingol", "elazig",
        "tunceli", "erzincan", "agri", "kars", "ardahan", "igdir", "bitlis", "siirt", "sanliurfa",
        "gaziantep", "kahramanmaras", "adiyaman", "osmaniye", "kilis", "hatay", "antakya",
        "iskenderun", "malatya", "sivas", "tokat", "amasya", "sinop", "rize", "trabzon",
        "giresun", "ordu", "samsun", "zonguldak", "bolu", "edirne", "kirklareli", "tekirdag",
        "canakkale", "balikesir", "manisa", "aydin", "mugla", "antalya", "isparta", "burdur",
        "denizli", "afyon", "usak", "kutahya", "bursa", "yalova", "sakarya", "duzce", "bartin",
        "kastamonu", "corum", "yozgat", "nevsehir", "kirsehir", "kirikkale", "ankara", "konya",
        "eskisehir", "kayseri", "nigde", "aksaray", "karaman", "mersin", "adana", "istanbul",
        "izmir", "bodrum", "fethiye","bilecik", "artvin", "bayburt", "cankiri", "erzurum",
        "gumushane", "karabuk",
    }
)


def _fold_tr(s: str) -> str:
    """ASCII-style fold so Balıkesir/balikesir/balıkesir all match."""
    x = _norm_for_place(s)
    for a, b in (
        ("ı", "i"),
        ("ğ", "g"),
        ("ü", "u"),
        ("ş", "s"),
        ("ö", "o"),
        ("ç", "c"),
    ):
        x = x.replace(a, b)
    return x


def _norm_for_place(s: str) -> str:
    return (
        s.replace("İ", "i")
        .replace("I", "ı")
        .lower()
        .replace("’", "'")
        .replace("`", "'")
    )


def _mentions_kocaeli_context(title: str, text: str) -> bool:
    blob = _norm_for_place(title + " " + text[:400])
    if "kocaeli" in blob:
        return True
    for d in KOCAELI_DISTRICTS:
        if _norm_for_place(d) in blob:
            return True
    return False


def _kocaeli_anchor_in_title(title: str) -> bool:
    """Local story: headline names Kocaeli or an ilçe (not boilerplate in body)."""
    nt = _fold_tr(title)
    if re.search(r"(?<![a-z0-9])kocaeli(?![a-z0-9])", nt):
        return True
    for d in KOCAELI_DISTRICTS:
        dl = _fold_tr(d)
        if re.search(rf"(?<![a-z0-9]){re.escape(dl)}(?:['']?[td][ae])?(?![a-z0-9])", nt):
            return True
    return False


def _mentions_other_turkey_place(title: str, text: str) -> bool:
    """
    Another province/city named in title + lead. If headline is not Kocaeli-anchored, reject for map.
    Scans body lead so 'Balıkesir' in first paragraphs is caught when title is vague.
    """
    lead = _fold_tr(title + " " + (text or "")[:1200])
    anchored = _kocaeli_anchor_in_title(title)
    for place in OTHER_TURKEY_PLACES:
        if re.search(
            rf"(?<![a-z0-9]){re.escape(place)}(?:['']?[td][ae])?(?![a-z0-9])",
            lead,
        ):
            if not anchored:
                return True
    return False


def extract_location_info(title: str, text: str) -> Optional[Dict[str, Any]]:
    """
    Mandatory PDF Requirement (Section 6):
    - Extract neighborhood (Mahalle), street (Sokak/Cadde) if present.
    - Avoid footer pollution by only parsing the top 500 characters.
    """
    if not text and not title:
        return None

    if _mentions_other_turkey_place(title, text):
        return None

    # Only search the title and top of text to avoid footer pollution (like newspaper address)
    search_text = title + " " + text[:500]
    text_clean = search_text.replace('İ', 'i').replace('I', 'ı').lower()
    
    # 1. Detect specific address parts first (Mahalle, Cadde, Sokak)
    specific_patterns = [
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Mahallesi)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Caddesi)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Bulvarı)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Sokağı)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Mevkii)'
    ]
    
    candidates: List[str] = []
    specific_loc: Optional[str] = None
    for pattern in specific_patterns:
        for match in re.finditer(pattern, search_text, re.I):
            candidate = match.group(1).strip()
            # Junk filter
            if any(junk in candidate.lower() for junk in ["haber", "sayfa", "site", "tıkla", "güncel", "yerel"]):
                continue
            candidates.append(candidate)
            if specific_loc is None:
                specific_loc = candidate
        if specific_loc is not None:
            break

    # 1b Hospital / clinic names (NER often misses "Devlet Hastanesi")
    if specific_loc is None:
        hm = re.search(
            r"\b((?:\w+\s+){0,2}?(?:Devlet|Şehir|Özel)\s+Hastanesi)(?:'[ns]?(?:de|da|nde|nda))?\b",
            search_text,
            re.I,
        )
        if not hm:
            hm = re.search(
                r"\b([A-ZÇĞİÖŞÜa-zçğıöşü]{2,25}\s+Hastanesi)(?:'[ns]?(?:de|da|nde|nda))?\b",
                search_text,
                re.I,
            )
        if hm:
            hosp = hm.group(1).strip()
            if not any(j in hosp.lower() for j in ("haber", "gündem", "son dakika")):
                specific_loc = hosp
                candidates.append(hosp)

    # 2. NER only when we still need hints (never used alone for map pin anymore)
    if specific_loc is None:
        nlp = get_stanza_nlp()
        if nlp:
            try:
                doc = nlp(search_text)
                for ent in doc.ents:
                    if ent.type == "LOC":
                        loc_name = ent.text
                        if len(loc_name) > 2 and not any(
                            junk in loc_name.lower() for junk in ["haber", "sayfa", "site"]
                        ):
                            if loc_name not in candidates:
                                candidates.append(loc_name)
            except Exception as e:
                print(f"Stanza NER extraction failed: {e}")

    # 3. Detect District as a fallback or secondary anchor (Keep for strict Kocaeli validation)
    districts_found = []
    district_positions = []
    
    # Suffixes: -da, -de, -dan, -den, -ya, -ye, -a, -e, -nın, -nin, -daki, -deki, -ndaki, -ndeki
    district_suffixes = r'(?:[\'’]?(?:da|de|ta|te|dan|den|tan|ten|ya|ye|a|e|ı|i|u|ü|nın|nin|nun|nün|nda|nde|ndan|nden|na|ne|lı|li|lu|lü|ki|daki|deki|taki|teki|ndaki|ndeki))?\b'

    title_clean = title.replace('İ', 'i').replace('I', 'ı').lower()
    district_in_title = False

    for district in KOCAELI_DISTRICTS:
        d_lower = district.replace('İ', 'i').replace('I', 'ı').lower()
        pattern = r'\b' + re.escape(d_lower) + district_suffixes
        
        # Check if it's in the title first - TITLES get ultimate priority
        if re.search(pattern, title_clean, re.I):
            district_in_title = True
            districts_found.insert(0, district)  # Put at the front
            if district not in candidates:
                candidates.append(district)
            district_positions.append((0, district))  # Weight 0 = Title
            continue
            
        # Otherwise search in body
        match = re.search(pattern, text_clean, re.I)
        if match:
            pos = match.start()
            districts_found.append(district)
            if district not in candidates:
                candidates.append(district)
            district_positions.append((pos, district))

    # 4. Combine results smartly
    district: Optional[str] = None

    # If we found a specific address part (Mahalle/Sokak) via regex, it's very high confidence
    if specific_loc:
        if len(districts_found) == 1 and districts_found[0] != "İzmit":
            district = districts_found[0]
            best = f"{specific_loc}, {district}, Kocaeli, Turkey"
        else:
            best = f"{specific_loc}, Kocaeli, Turkey"

        return {
            "best_location_text": best,
            "district": district,
            "candidates": sorted(set(candidates)),
        }
    
    # District-only:
    # - If ilçe is in the headline -> high confidence.
    # - If ilçe is only in the body, allow it only when it appears early (near the top),
    #   to avoid false pins from generic / late mentions.
    if district_positions:
        district_positions.sort(key=lambda x: x[0])
        earliest_pos = district_positions[0][0] if district_positions else 999999
        if not district_in_title and earliest_pos > 220:
            return None
        ordered_districts = [d for pos, d in district_positions]
        if len(ordered_districts) > 1 and ordered_districts[0] == "İzmit":
            district = ordered_districts[1]
        else:
            district = ordered_districts[0]
        # Do not prepend Stanza LOC (e.g. "Dere") — causes false merges with ilçe names.
        best_loc = f"{district}, Kocaeli, Turkey"
        return {
            "best_location_text": best_loc,
            "district": district,
            "candidates": sorted(set(candidates)),
        }

    return None


async def get_coordinates(db: AsyncIOMotorDatabase, location_name: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Calls Google Maps Geocoding API to get Latitude and Longitude.
    STRICT VALIDATION: Rejects mapped coordinates if they fall outside Kocaeli Province.
    """
    if not location_name:
        return None, None

    if not API_KEY:
        print("GOOGLE_MAPS_API_KEY is missing; cannot geocode.")
        return None, None

    gmaps = get_gmaps_client()
    if gmaps is None:
        print("Google Maps client is unavailable; cannot geocode.")
        return None, None

    key = _cache_key(location_name)
    cached = await db.geocache.find_one({"key": key})
    if cached and "lat" in cached and "lng" in cached:
        return cached.get("lat"), cached.get("lng")

    try:
        result = await asyncio.to_thread(lambda: gmaps.geocode(location_name))
        if result:
            # Strict safety filter: ensure Google didn't map "Yalıkavak, Kocaeli" to "Bodrum, Muğla"
            address = result[0].get("formatted_address", "")
            if "Kocaeli" not in address:
                print(f"Skipping {location_name}: Google mapped it outside Kocaeli -> {address}")
                return None, None
                
            loc = result[0].get("geometry", {}).get("location", {})
            lat, lng = loc.get("lat"), loc.get("lng")
            if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                await db.geocache.update_one(
                    {"key": key},
                    {"$set": {"key": key, "query": location_name, "lat": lat, "lng": lng}},
                    upsert=True,
                )
                return float(lat), float(lng)
    except Exception as e:
        print(f"Google Geocoding failed for {location_name}: {e}")

    return None, None


def extract_location_from_text(text: str) -> Optional[str]:
    """
    Backwards-compatible helper for older callers.
    Returns best_location_text or None.
    """
    info = extract_location_info("", text)
    if not info:
        return None
    return info["best_location_text"]
