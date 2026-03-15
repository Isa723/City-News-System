import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from services.scraper import scrape_all_sources
from services.nlp import classify_news, is_duplicate
from services.geocoding import extract_location_from_text, get_coordinates

MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.kocaeli_news
news_collection = db.news

async def run_pipeline():
    print("🚀 Starting the unified Scraper -> NLP -> Map Pipeline...")
    
    # 1. Scrape all raw news from 5 sites (last 3 days)
    print("⏳ Fetching RSS feeds and parsing HTML...")
    raw_news_list = await scrape_all_sources()
    print(f"✅ Found {len(raw_news_list)} recent news items in total.")
    
    # Fetch all existing texts from DB for duplicate checking efficiently
    # If the DB is very large, this should be paginated or indexed,
    # but for local recent news, this is extremely fast.
    existing_records = await news_collection.find({}, {"content": 1}).to_list(length=None)
    existing_texts = [r["content"] for r in existing_records if "content" in r]
    
    saved_count = 0
    
    for item in raw_news_list:
        content = item['content']
        title = item['title']
        
        # 2. Prevent Duplicates (Exact URL)
        exists = await news_collection.find_one({"url": item["url"]})
        if exists:
            continue
            
        # 2. Prevent Duplicates (%90 Similarity embedding check per PDF rules)
        print(f"🧠 Checking '{title}' for semantic duplicates...")
        duplicate, score = is_duplicate(content, existing_texts)
        if duplicate:
            print(f"   ❌ Duplicate rejected (Similarity {score*100:.1f}%)")
            continue
            
        # 3. Classify News (Trafik, Yangın vs.)
        category = classify_news(content)
        item['category'] = category
        
        # 4. Extract Location and Geocode
        location_text = extract_location_from_text(content)
        if not location_text:
            # Drop if strict coordinate visualizer is mandated, but PDF says:
            # "Konum bulunamazsa, haber haritada gösterilmemelidir."
            # We save it anyway, but with no coordinates, frontend will hide it.
            item['location_text'] = "Belirtilmemiş"
            item['latitude'] = None
            item['longitude'] = None
        else:
            item['location_text'] = location_text
            lat, lng = get_coordinates(location_text)
            item['latitude'] = lat
            item['longitude'] = lng
            
        # 5. Save to MongoDB
        await news_collection.insert_one(item)
        existing_texts.append(content)  # Update in-memory texts to prevent duplicates within the same batch
        saved_count += 1
        print(f"   ✅ Saved: [{category}] {title}")
        
    print(f"🎉 Pipeline finished successfully. {saved_count} fresh news items added to Database.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
