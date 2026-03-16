from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

async def clean_db():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client.kocaeli_news
    await db.news.delete_many({})
    print("Database cleared successfully.")

if __name__ == "__main__":
    asyncio.run(clean_db())
