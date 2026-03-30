import motor.motor_asyncio
import asyncio

async def check():
    client = motor.motor_asyncio.AsyncIOMotorClient('mongodb://localhost:27017')
    db = client['kocaeli_news']
    total = await db.news.count_documents({})
    news = await db.news.find().sort('publish_date', -1).limit(10).to_list(10)
    
    print(f"Total News in DB: {total}")
    for n in news:
        s_list = n.get('sources', [])
        source_name = s_list[0].get('name') if s_list else 'Unknown'
        url = s_list[0].get('url') if s_list else 'None'
        print(f"[{source_name}] {n.get('title')[:60]}... URL: {url}")

if __name__ == "__main__":
    asyncio.run(check())
