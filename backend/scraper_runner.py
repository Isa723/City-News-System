import argparse
import asyncio
from datetime import datetime, timedelta, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from services.scraper import scrape_all_sources
from services.nlp import classify_news, is_duplicate
from services.geocoding import extract_location_info, get_coordinates

MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.kocaeli_news
news_collection = db.news

def _default_date_range_iso():
    now = datetime.now(timezone.utc)
    date_to = now.isoformat()
    date_from = (now - timedelta(days=3)).isoformat()
    return date_from, date_to


async def run_pipeline(date_from: str | None = None, date_to: str | None = None):
    print("🚀 Starting the unified Scraper -> NLP -> Map Pipeline...")
    
    # 1. Scrape all raw news from 5 sites (last 3 days)
    print("⏳ Fetching RSS feeds and parsing HTML...")
    if not date_from and not date_to:
        date_from, date_to = _default_date_range_iso()
    raw_news_list = await scrape_all_sources(date_from=date_from, date_to=date_to)
    print(f"✅ Found {len(raw_news_list)} recent news items in total.")
    
    # Fetch recent existing records for duplicate checking (keep it efficient).
    now = datetime.now(timezone.utc)
    seven_days_ago = (now - timedelta(days=7)).isoformat()
    existing_records = await news_collection.find(
        {"publish_date": {"$gte": seven_days_ago}},
        {"content": 1},
    ).to_list(length=None)
    
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
        duplicate, score, matched_id = is_duplicate(content, existing_records)
        
        if duplicate:
            print(f"   🔗 Duplicate found ({score*100:.1f}%), adding {source_name} to sources list.")
            await news_collection.update_one(
                {"_id": matched_id},
                {"$addToSet": {"sources": {"name": source_name, "url": url}}}
            )
            continue
            
        # 3. Classify News (Trafik, Yangın vs. - passing title for priority)
        category = classify_news(content, title=title)
        # Skip unrelated categories to keep DB focused on required types
        if category == "Diğer":
            print(f"   [!] Category 'Diğer' for '{title[:60]}...' -> skipping.")
            continue
        
        # Prepare item for insertion with sources list
        db_item = {
            "title": title,
            "content": content,
            "category": category,
            "publish_date": item["publish_date"],
            "sources": [{"name": source_name, "url": url}]
        }
        
        # 4. Extract Location (structured) and Geocode
        # STRICT KOCAELI REQUIREMENT (PDF Section 2: Yalnızca Kocaeli)
        KOCAELI_KEYWORDS = ["kocaeli", "izmit", "gebze", "gölcük", "derince", "darıca", "körfez", "kartepe", "başiskele", "karamürsel", "kandıra", "dilovası", "çayırova"]
        if not any(k in content.lower() or k in title.lower() for k in KOCAELI_KEYWORDS):
            print(f"   [!] Non-Kocaeli national news detected ('{title}'). Skipping.")
            continue

        loc_info = extract_location_info(content)
        if not loc_info:
            print(f"   [!] No location found for '{title}'. Skipping.")
            continue

        location_text = loc_info["best_location_text"]
        lat, lng = await get_coordinates(db, location_text)
        if lat is None or lng is None:
            print(f"   [!] Geocoding failed for '{location_text}'. Skipping.")
            continue
            
        db_item['location_text'] = location_text
        db_item['district'] = loc_info.get("district")
        db_item['location_candidates'] = loc_info.get("candidates", [])
        db_item['latitude'] = lat
        db_item['longitude'] = lng
            
        # 5. Save to MongoDB
        await news_collection.insert_one(db_item)
        existing_records.append({"_id": None, "content": content})
        saved_count += 1
        print(f"   ✅ Saved: [{category}] {title}")
        
    print(f"🎉 Pipeline finished successfully. {saved_count} fresh news items added to Database.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date-from", dest="date_from", default=None, help="ISO datetime start (inclusive)")
    parser.add_argument("--date-to", dest="date_to", default=None, help="ISO datetime end (inclusive)")
    args = parser.parse_args()

    # Validate ISO if provided (accept Z)
    if args.date_from:
        datetime.fromisoformat(args.date_from.replace("Z", "+00:00"))
    if args.date_to:
        datetime.fromisoformat(args.date_to.replace("Z", "+00:00"))

    asyncio.run(run_pipeline(date_from=args.date_from, date_to=args.date_to))
