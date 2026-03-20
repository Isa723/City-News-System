import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from backend.services.nlp import classify_news

MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.kocaeli_news
news_collection = db.news

async def main():
    cursor = news_collection.find({})
    to_delete = []
    
    async for news in cursor:
        category = classify_news(news.get("content", ""), title=news.get("title", ""))
        if category == "Diğer":
            to_delete.append(news["_id"])
            
    if to_delete:
        await news_collection.delete_many({"_id": {"$in": to_delete}})
        print(f"Deleted {len(to_delete)} false-positive news from the database.")
    else:
        print("No false-positive news found.")

if __name__ == "__main__":
    asyncio.run(main())
