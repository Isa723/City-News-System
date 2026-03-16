from motor.motor_asyncio import AsyncIOMotorClient
import asyncio
import json

async def audit_categories():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.kocaeli_news
    
    news_list = await db.news.find({}, {"title": 1, "category": 1, "location_text": 1}).to_list(length=100)
    
    with open("audit_final.txt", "w", encoding="utf-8") as f:
        f.write(f"{'TITLE':<60} | {'CATEGORY':<20} | {'LOCATION'}\n")
        f.write("-" * 110 + "\n")
        for n in news_list:
            f.write(f"{n['title'][:58]:<60} | {n['category']:<20} | {n.get('location_text')}\n")

if __name__ == "__main__":
    asyncio.run(audit_categories())
