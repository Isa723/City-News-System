from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn
import os

app = FastAPI(title="Kocaeli Local News Map API")

# Setup CORS to allow the frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB Connection String
MONGO_URL = "mongodb://localhost:27017"
client = None
db = None

# Pydantic Model for a News Item
class NewsItem(BaseModel):
    title: str
    content: str
    category: str
    location_text: str
    latitude: Optional[float]
    longitude: Optional[float]
    publish_date: str
    source: str
    url: str

@app.on_event("startup")
async def startup_db_client():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.kocaeli_news

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

@app.get("/")
async def root():
    return {"message": "Welcome to Kocaeli Local News Map API"}

@app.get("/api/news", response_model=List[NewsItem])
async def get_news(
    category: Optional[str] = None,
    source: Optional[str] = None
):
    """
    Get all news, optionally filtered by category or source
    """
    query = {}
    if category:
        query["category"] = category
    if source:
        query["source"] = source
        
    news_cursor = db.news.find(query).sort("publish_date", -1)
    news_list = []
    
    async for document in news_cursor:
        # Convert ObjectId to string for JSON serialization
        document["_id"] = str(document["_id"])
        news_list.append(document)
        
    return news_list

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
