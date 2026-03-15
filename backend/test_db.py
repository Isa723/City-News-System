import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

async def ping_server():
    try:
        # Connect to local MongoDB
        client = AsyncIOMotorClient("mongodb://localhost:27017")
        
        # Ping the server to check connection
        response = await client.admin.command('ping')
        
        if response.get('ok') == 1.0:
            print("✅ Successfully connected to MongoDB locally!")
        else:
            print("❌ Connected to MongoDB, but received unexpected response:", response)
            
    except Exception as e:
        print("❌ Could not connect to MongoDB. Is the MongoDB service running?")
        print(f"Error details: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(ping_server())
