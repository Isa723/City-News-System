import googlemaps
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=API_KEY)

districts = [
    "İzmit", "Gebze", "Gölcük", "Derince", "Darıca", 
    "Körfez", "Kartepe", "Başiskele", "Karamürsel", 
    "Kandıra", "Dilovası", "Çayırova"
]

print(f"Testing Google Geocoding for Kocaeli Districts (Key: {API_KEY[:5]}...{API_KEY[-5:]})")

for d in districts:
    query = f"{d}, Kocaeli, Turkey"
    res = gmaps.geocode(query)
    if res:
        loc = res[0]['geometry']['location']
        addr = res[0]['formatted_address']
        print(f"[{d}] -> {addr} | Coords: {loc['lat']}, {loc['lng']}")
    else:
        print(f"[{d}] -> FAILED")
