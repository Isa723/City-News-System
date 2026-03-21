from __future__ import annotations

import asyncio
import googlemaps
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorDatabase

# Load environment variables
load_dotenv()

# Initialize Google Maps Client
# Mandatory Requirement (Section 7): "API anahtarı güvenli biçimde saklanmalıdır."
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)

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

    # 2. Detect District as a fallback or secondary anchor
    districts_found = []
    for district in KOCAELI_DISTRICTS:
        d_lower = district.replace('İ', 'i').replace('I', 'ı').lower()
        if re.search(r'\b' + re.escape(d_lower) + r'\b', text_clean):
            districts_found.append(district)
            candidates.append(district)

    # 3. Combine results smartly
    district: Optional[str] = None

    if specific_loc:
        if len(districts_found) == 1 and districts_found[0] != "İzmit":
            district = districts_found[0]
            best = f"{specific_loc}, {districts_found[0]}, Kocaeli, Turkey"
        else:
            best = f"{specific_loc}, Kocaeli, Turkey"

        return {
            "best_location_text": best,
            "district": district,
            "candidates": sorted(set(candidates)),
        }
            
    if districts_found:
        if len(districts_found) > 1 and "İzmit" in districts_found:
            other_districts = [d for d in districts_found if d != "İzmit"]
            district = other_districts[0]
        else:
            district = districts_found[0]

        return {
            "best_location_text": f"{district}, Kocaeli, Turkey",
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
