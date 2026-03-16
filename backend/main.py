from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import subprocess

app = FastAPI(title="Kocaeli Local News Map API")

# Setup CORS to allow the frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount the frontend directory to serve static HTML/CSS/JS files
# This makes the app available at http://localhost:8000/
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

# MongoDB Connection String
MONGO_URL = "mongodb://localhost:27017"
client = None
db = None

# Pydantic Model for a News Item
class SourceItem(BaseModel):
    name: str
    url: str

class NewsItem(BaseModel):
    title: str
    content: str
    category: str
    location_text: str
    latitude: Optional[float]
    longitude: Optional[float]
    publish_date: str
    sources: List[SourceItem]

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
        query["sources.name"] = source
        
    news_cursor = db.news.find(query).sort("publish_date", -1)
    news_list = []
    
    async for document in news_cursor:
        # Convert ObjectId to string for JSON serialization
        document["_id"] = str(document["_id"])
        news_list.append(document)
        
    return news_list

@app.post("/api/scrape")
async def trigger_scraper():
    """
    Triggers the scraping pipeline in the background.
    """
    try:
        # Get the path to the current virtual environment's python
        venv_python = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe")
        if not os.path.exists(venv_python):
            venv_python = "python" # Fallback
            
        # Run the standalone scraper script async
        subprocess.Popen([venv_python, "backend/scraper_runner.py"])
        return {"status": "success", "message": "Scraping started in the background..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
