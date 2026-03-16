import asyncio
from backend.services.scraper import scrape_all_sources
from backend.services.geocoding import extract_location_from_text, get_coordinates

async def debug_extraction():
    print("Fetching raw news samples...")
    news_list = await scrape_all_sources()
    print(f"Total found: {len(news_list)}")
    
    success_count = 0
    for i, item in enumerate(news_list[:20]): # Check first 20
        title = item['title']
        content = item['content']
        loc = extract_location_from_text(content)
        
        if loc:
            lat, lng = get_coordinates(loc)
            if lat:
                print(f"[{i}] SUCCESS | {title} | Loc: {loc} | Coords: {lat}, {lng}")
                success_count += 1
            else:
                print(f"[{i}] GEO-FAIL | {title} | Loc: {loc}")
        else:
            print(f"[{i}] LOC-FAIL | {title} | Content Snippet: {content[:100]}...")

    print(f"\nSummary: {success_count}/20 succeeded.")

if __name__ == "__main__":
    asyncio.run(debug_extraction())
