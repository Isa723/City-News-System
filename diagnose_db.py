from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def diagnose():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.kocaeli_news
    
    # 1. Check schemas
    total = await db.news.count_documents({})
    with_sources = await db.news.count_documents({"sources": {"$exists": True}})
    old_schema = await db.news.count_documents({"source": {"$exists": True}})
    
    print(f"Total News: {total}")
    print(f"News with new schema (sources list): {with_sources}")
    print(f"News with old schema (source string): {old_schema}")
    
    # 2. Check geocoding variety
    pipeline = [
        {"$match": {"latitude": {"$ne": None}}},
        {"$group": {"_id": {"lat": "$latitude", "lng": "$longitude"}, "count": {"$sum": 1}, "locations": {"$addToSet": "$location_text"}}}
    ]
    coords = await db.news.aggregate(pipeline).to_list(length=None)
    print("\nDistinct Coordinates in DB:")
    for c in coords:
        print(f"Coords: {c['_id']} | Count: {c['count']} | Sample Locations: {c['locations'][:3]}")

if __name__ == "__main__":
    asyncio.run(diagnose())
