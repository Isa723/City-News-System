import googlemaps
import os
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Google Maps Client
# Mandatory Requirement (Section 7): "API anahtarı güvenli biçimde saklanmalıdır."
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)

# Simple in-memory cache to prevent duplicate API calls for the same location
# as requested by the assignment: "Aynı konum için gereksiz tekrar API çağrısı yapılmamalıdır"
location_cache = {}

# List of Kocaeli Districts to extract from text
KOCAELI_DISTRICTS = [
    "İzmit", "Gebze", "Gölcük", "Derince", "Darıca", 
    "Körfez", "Kartepe", "Başiskele", "Karamürsel", 
    "Kandıra", "Dilovası", "Çayırova"
]

def extract_location_from_text(text):
    """
    Mandatory PDF Requirement (Section 6):
    - Extract neighborhood (Mahalle), street (Sokak/Cadde) if present.
    - Return the MOST SPECIFIC location string.
    - PREVENT İzmit bias: Do not force "İzmit" just because it's mentioned in the text.
    """
    if not text:
        return None
        
    text_clean = text.replace('İ', 'i').replace('I', 'ı').lower()
    
    # 1. Detect specific address parts first (Mahalle, Cadde, Sokak)
    # These are highly unique and Google can find the district from them.
    specific_patterns = [
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Mahallesi)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Caddesi)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Bulvarı)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Sokağı)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9\s]+ Mevkii)'
    ]
    
    specific_loc = None
    for pattern in specific_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            candidate = match.group(1).strip()
            # Junk filter
            if any(junk in candidate.lower() for junk in ["haber", "sayfa", "site", "tıkla", "güncel", "yerel"]):
                continue
            specific_loc = candidate
            break

    # 2. Detect District as a fallback or secondary anchor
    districts_found = []
    for district in KOCAELI_DISTRICTS:
        d_lower = district.replace('İ', 'i').replace('I', 'ı').lower()
        if re.search(r'\b' + re.escape(d_lower) + r'\b', text_clean):
            districts_found.append(district)

    # 3. Combine results smartly
    # Priority A: If we have a specific neighborhood/street, let Google find the district.
    # We only append a district if we found only ONE district and it's NOT just mentioned as a generic tag.
    if specific_loc:
        # If we have a district but multiple were found, or it's 'İzmit' (common default), 
        # just send the specific loc + Kocaeli. Google is smarter than our regex.
        if len(districts_found) == 1 and districts_found[0] != "İzmit":
            return f"{specific_loc}, {districts_found[0]}, Kocaeli, Turkey"
        else:
            return f"{specific_loc}, Kocaeli, Turkey"
            
    # Priority B: If no neighborhood, but we found a distinct district
    if districts_found:
        # Bias check: if 'İzmit' is found with others, prioritize the other one 
        # (Since İzmit is often mentioned as the central tag)
        if len(districts_found) > 1 and "İzmit" in districts_found:
            other_districts = [d for d in districts_found if d != "İzmit"]
            return f"{other_districts[0]}, Kocaeli, Turkey"
        return f"{districts_found[0]}, Kocaeli, Turkey"
        
    return None

def get_coordinates(location_name):
    """
    Calls Google Maps Geocoding API to get Latitude and Longitude.
    Uses caching to avoid redundant calls.
    Returns (latitude, longitude) or (None, None) if failed.
    """
    if not location_name:
        return None, None
        
    # Check cache first
    if location_name in location_cache:
        return location_cache[location_name]
        
    try:
        # Geocoding using official Google Maps Client
        result = gmaps.geocode(location_name)
        
        if result:
            location = result[0]['geometry']['location']
            coords = (location['lat'], location['lng'])
            # Save to cache
            location_cache[location_name] = coords
            return coords
            
    except Exception as e:
        print(f"Google Geocoding failed for {location_name}: {e}")
        
    return None, None
