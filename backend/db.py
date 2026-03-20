from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase


async def ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    news = db.news
    geocache = db.geocache

    # News indexes (filters + duplicate prevention helpers)
    await news.create_index("publish_date")
    await news.create_index([("category", 1), ("district", 1), ("publish_date", -1)])
    await news.create_index("sources.url")
    await news.create_index("district")

    # Geocoding cache (durable, avoids repeated API calls)
    await geocache.create_index("key", unique=True)
