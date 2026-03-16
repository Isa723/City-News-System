from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def check_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.kocaeli_news
    count = await db.news.count_documents({})
    print(f"Total News in DB: {count}")
    
    with_coords = await db.news.count_documents({"latitude": {"$ne": None}})
    print(f"News with valid coordinates: {with_coords}")
    
    no_coords = await db.news.count_documents({"latitude": None})
    print(f"News with NULL coordinates: {no_coords}")
    
    sample = await db.news.find().limit(10).to_list(10)
    print("\nSample Data:")
    for s in sample:
        print(f"- {s['title']} | Location: {s.get('location_text')} | Coords: {s.get('latitude')}, {s.get('longitude')}")

if __name__ == "__main__":
    asyncio.run(check_db())
