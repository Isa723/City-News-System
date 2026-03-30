import motor.motor_asyncio
import asyncio

async def check():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['kocaeli_news']
    # Get total count
    total = await db.news.count_documents({})
    # Get 3-day count (approximate by sorting and matching recent)
    news = await db.news.find().sort('publish_date', -1).limit(60).to_list(60)
    
    sources = {}
    for n in news:
        s = n.get('source', 'Unknown')
        sources[s] = sources.get(s, 0) + 1
    
    print(f"Total in DB: {total}")
    print(f"Distribution of recent 60 items: {sources}")
    if news:
        print(f"Latest URL: {news[0].get('url', 'No URL')}")

if __name__ == "__main__":
    asyncio.run(check())
