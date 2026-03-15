from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import time
import re

# Initialize Nominatim geocoder (Free OpenStreetMap Geocoding)
# User_agent is required by their terms of service
geolocator = Nominatim(user_agent="kocaeli_news_scraper_v1")

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
    Searches the news text for known Kocaeli districts or neighborhoods.
    Returns the most specific location string found.
    """
    if not text:
        return None
        
    text_upper = text.upper()
    
    # Simple district matching
    # In a real-world scenario, we would use NER (Named Entity Recognition),
    # but for this assignment, finding the district name is sufficient.
    found_districts = []
    for district in KOCAELI_DISTRICTS:
        if re.search(r'\b' + re.escape(district.upper()) + r'\b', text_upper):
            found_districts.append(district)
            
    if found_districts:
        # If multiple districts are mentioned, we take the first one found 
        # or combine them, but Nominatim works best with a single specific location.
        # We append "Kocaeli" to ensure geocoding finds the right province.
        loc = f"{found_districts[0]}, Kocaeli, Turkey"
        return loc
        
    return None

def get_coordinates(location_name):
    """
    Calls Nominatim API to get Latitude and Longitude.
    Uses caching to avoid redundant calls.
    Returns (latitude, longitude) or (None, None) if failed.
    """
    if not location_name:
        return None, None
        
    # Check cache first
    if location_name in location_cache:
        return location_cache[location_name]
        
    try:
        # Adding a small delay to respect Nominatim usage limits (1 request per second)
        time.sleep(1.1)
        location = geolocator.geocode(location_name, timeout=10)
        
        if location:
            coords = (location.latitude, location.longitude)
            # Save to cache
            location_cache[location_name] = coords
            return coords
            
    except (GeocoderTimedOut, GeocoderUnavailable) as e:
        print(f"Geocoding failed for {location_name}: {e}")
        
    return None, None
