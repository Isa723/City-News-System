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
        source_name = item['source']
        url = item['url']
        
        # 2. Prevent Exact Duplicates (Check if this URL is already in any source list)
        exists = await news_collection.find_one({"sources.url": url})
        if exists:
            # We already have this exact article from this source
            continue
            
        # 2. Prevent Semantic Duplicates (%90 Similarity)
        # Requirement: "Farklı haber kaynaklarında yer alan ancak içerik olarak aynı olan 
        # haberler tek bir haber olarak değerlendirilmelidir. Haber kaynaklarının tümü listelenmelidir."
        print(f"🧠 Checking '{title}' for semantic duplicates...")
        duplicate, score, matched_text = is_duplicate(content, existing_texts)
        
        if duplicate:
            print(f"   🔗 Duplicate found ({score*100:.1f}%), adding {source_name} to sources list.")
            await news_collection.update_one(
                {"content": matched_text},
                {"$addToSet": {"sources": {"name": source_name, "url": url}}}
            )
            continue
            
        # 3. Classify News (Trafik, Yangın vs. - passing title for priority)
        category = classify_news(content, title=title)
        
        # Prepare item for insertion with sources list
        db_item = {
            "title": title,
            "content": content,
            "category": category,
            "publish_date": item["publish_date"],
            "sources": [{"name": source_name, "url": url}]
        }
        
        # 4. Extract Location and Geocode
        location_text = extract_location_from_text(content)
        if not location_text:
            print(f"   [!] No location found for '{title}'. Skipping.")
            continue
            
        lat, lng = get_coordinates(location_text)
        if lat is None or lng is None:
            print(f"   [!] Geocoding failed for '{location_text}'. Skipping.")
            continue
            
        db_item['location_text'] = location_text
        db_item['latitude'] = lat
        db_item['longitude'] = lng
            
        # 5. Save to MongoDB
        await news_collection.insert_one(db_item)
        existing_texts.append(content)
        saved_count += 1
        print(f"   ✅ Saved: [{category}] {title}")
        
    print(f"🎉 Pipeline finished successfully. {saved_count} fresh news items added to Database.")

if __name__ == "__main__":
    asyncio.run(run_pipeline())
