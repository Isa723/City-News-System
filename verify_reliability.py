from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import re

async def check_raw_coverage():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.kocaeli_news
    
    news_list = await db.news.find({}).to_list(length=100)
    
    print(f"Total News in DB: {len(news_list)}")
    print("-" * 50)
    
    # Critical keywords to look for manually
    test_keywords = {
        "Kaza": ["kaza", "çarpışt", "devrild"],
        "Yangın": ["yangın", "alev", "itfaiy"],
        "Hırsızlık": ["hırsız", "çalınd", "soygun"],
        "Kesinti": ["kesinti", "sedaş", "elektrik"]
    }
    
    matches_found = 0
    for n in news_list:
        title = n['title']
        content = n['content']
        text = (title + " " + content).lower()
        
        found_types = []
        for cat, kws in test_keywords.items():
            if any(kw in text for kw in kws):
                found_types.append(cat)
        
        if found_types:
            print(f"[!] POTENTIAL MATCH | {title[:50]}... | Found: {found_types} | Current Cat: {n['category']}")
            matches_found += 1
            
    if matches_found == 0:
        print("✅ Audited all news: No mentions of Accidents, Fire, or Theft found in raw content.")
    else:
        print(f"\nFound {matches_found} potential items that might need stricter or looser classification.")

if __name__ == "__main__":
    asyncio.run(check_raw_coverage())
