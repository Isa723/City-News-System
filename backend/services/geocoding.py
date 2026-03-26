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

def extract_location_info(title: str, text: str) -> Optional[Dict[str, Any]]:
    """
    Mandatory PDF Requirement (Section 6):
    - Extract neighborhood (Mahalle), street (Sokak/Cadde) if present.
    - Avoid footer pollution by only parsing the top 500 characters.
    """
    if not text and not title:
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

    # 2. Use Stanza NER to find LOC entities (AI-based extraction)
    nlp = get_stanza_nlp()
    if nlp:
        try:
            doc = nlp(search_text)
            for ent in doc.ents:
                if ent.type == "LOC":
                    loc_name = ent.text
                    # Avoid very short or junk entities
                    if len(loc_name) > 2 and not any(junk in loc_name.lower() for junk in ["haber", "sayfa", "site"]):
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
    
    for district in KOCAELI_DISTRICTS:
        d_lower = district.replace('İ', 'i').replace('I', 'ı').lower()
        pattern = r'\b' + re.escape(d_lower) + district_suffixes
        
        # Check if it's in the title first - TITLES get ultimate priority
        if re.search(pattern, title_clean, re.I):
            districts_found.insert(0, district) # Put at the front
            if district not in candidates:
                candidates.append(district)
            district_positions.append((0, district)) # Weight 0 = Title
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
    
    # If no specific_loc but we have NER LOC candidates
    # We filter them to ensure they are likely in Kocaeli by checking if a district is also present
    if district_positions:
        # Sort by position (Title=0, then earliest in text)
        district_positions.sort(key=lambda x: x[0])
        ordered_districts = [d for pos, d in district_positions]
        
        if len(ordered_districts) > 1 and ordered_districts[0] == "İzmit":
            district = ordered_districts[1]
        else:
            district = ordered_districts[0]

        # Check if any NER candidate looks like it belongs to this district
        # Otherwise just use the district
        best_loc = f"{district}, Kocaeli, Turkey"
        
        # If the earliest LOC from Stanza isn't the district itself, use it as a specific location
        # but only if it's not a known district (to avoid redundancy like "Gebze, Gebze")
        for cand in candidates:
            if cand not in KOCAELI_DISTRICTS and cand not in districts_found:
                # High probability this is a Mahalle or specific place in the district
                best_loc = f"{cand}, {district}, Kocaeli, Turkey"
                break

        return {
            "best_location_text": best_loc,
            "district": district,
            "candidates": sorted(set(candidates)),
        }
        
    # Final fallback: If NER found something but no district was matched, still try it with Kocaeli anchor
    if candidates:
        return {
            "best_location_text": f"{candidates[0]}, Kocaeli, Turkey",
            "district": None,
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
