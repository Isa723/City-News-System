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
    - Return the most specific location string.
    """
    if not text:
        return None
        
    text_clean = text.replace('İ', 'i').replace('I', 'ı').lower()
    
    # 1. Detect District (Anchor)
    district_found = None
    for district in KOCAELI_DISTRICTS:
        d_lower = district.replace('İ', 'i').replace('I', 'ı').lower()
        if re.search(r'\b' + re.escape(d_lower) + r'\b', text_clean):
            district_found = district
            break
            
    # 2. Detect specific address parts (Mahalle, Cadde, Sokak)
    specific_patterns = [
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9]+ Mahallesi)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9]+ Caddesi)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9]+ Bulvarı)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9]+ Sokağı)',
        r'([A-ZÇĞİÖŞÜa-zçğıöşü0-9]+ Mevkii)'
    ]
    
    specific_loc = None
    for pattern in specific_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            candidate = match.group(1).strip()
            if any(junk in candidate.lower() for junk in ["haber", "sayfa", "site", "tıkla"]):
                continue
            specific_loc = candidate
            break

    # 3. Combine results
    if specific_loc and district_found:
        return f"{specific_loc}, {district_found}, Kocaeli, Turkey"
    elif specific_loc:
        return f"{specific_loc}, Kocaeli, Turkey"
    elif district_found:
        return f"{district_found}, Kocaeli, Turkey"
        
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
