from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
import uvicorn
import os
import subprocess
import sys
from datetime import datetime
from dotenv import load_dotenv

from backend.db import ensure_indexes
from backend.models.news import NewsItem

# Load .env from project root so /api/config can read keys reliably.
project_root = os.path.dirname(os.path.dirname(__file__))
load_dotenv(os.path.join(project_root, ".env"))

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
frontend_path = os.path.join(project_root, "frontend")
app.mount("/app", StaticFiles(directory=frontend_path, html=True), name="frontend")

# MongoDB Connection String
MONGO_URL = "mongodb://localhost:27017"
client = None
db = None

@app.on_event("startup")
async def startup_db_client():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client.kocaeli_news
    await ensure_indexes(db)

    # Optional: automatic scraping on startup (PDF: scraping must be automatic).
    # Enable with SCRAPE_ON_STARTUP=true in environment.
    scrape_on_startup = os.getenv("SCRAPE_ON_STARTUP", "").strip().lower() in {"1", "true", "yes", "on"}
    if scrape_on_startup:
        try:
            venv_python = os.path.join(os.getcwd(), ".venv", "Scripts", "python.exe")
            if not os.path.exists(venv_python):
                venv_python = "python"
            subprocess.Popen([venv_python, "backend/scraper_runner.py"])
        except Exception as e:
            # Don't break server startup if scraping fails to spawn.
            print(f"SCRAPE_ON_STARTUP spawn failed: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

@app.get("/")
async def root():
    return {"message": "Welcome to Kocaeli Local News Map API"}


@app.get("/api/config")
async def get_public_config():
    """
    Public config for frontend bootstrap.
    Do NOT hardcode API keys in frontend files.
    """
    maps_js_key = os.getenv("GOOGLE_MAPS_JS_API_KEY") or os.getenv("GOOGLE_MAPS_API_KEY")
    return {"googleMapsJsApiKey": maps_js_key or ""}


@app.get("/api/news", response_model=List[NewsItem])
async def get_news(
    category: Optional[str] = None,
    district: Optional[str] = None,
    source: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    """
    Get news filtered by category/district/source/date range.
    """
    query: dict = {
        "category": {"$ne": "Diğer"},
        "latitude": {"$ne": None},
        "longitude": {"$ne": None},
    }
    if category:
        query["category"] = category
    if district:
        query["district"] = district
    if source:
        query["sources.name"] = source

    # ISO strings stored; keep filtering via ISO strings (lexicographically sortable)
    if date_from or date_to:
        date_query: dict = {}
        if date_from:
            # validate parsable
            datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            date_query["$gte"] = date_from
        if date_to:
            datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            date_query["$lte"] = date_to
        query["publish_date"] = date_query
        
    news_cursor = db.news.find(query).sort("publish_date", -1)
    news_list = []
    
    async for document in news_cursor:
        # Convert ObjectId to string for JSON serialization
        document["_id"] = str(document["_id"])
        news_list.append(document)
        
    return news_list

scraper_process = None

@app.post("/api/scrape")
async def trigger_scraper(date_from: Optional[str] = None, date_to: Optional[str] = None):
    """
    Triggers the scraping pipeline in the background.
    """
    global scraper_process
    try:
        # If already running, don't start another
        if scraper_process and scraper_process.poll() is None:
            return {"status": "already_running", "message": "Scraping is already in progress."}

        # Same interpreter as this API process (works with .venv, external venv, or global).
        # Avoid hard-coding .venv: if it was removed, "python" fallback often lacks deps.
        scraper_script = os.path.join(project_root, "backend", "scraper_runner.py")
        args = [sys.executable, scraper_script]
        if date_from:
            args += ["--date-from", date_from]
        if date_to:
            args += ["--date-to", date_to]

        scraper_process = subprocess.Popen(args, cwd=project_root)
        return {"status": "success", "message": "Scraping started in the background..."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/scrape/status")
async def get_scrape_status():
    """
    Returns the current status of the background scraper.
    """
    global scraper_process
    if scraper_process is None:
        return {"status": "idle"}
    
    poll = scraper_process.poll()
    if poll is None:
        return {"status": "running"}
    else:
        return {"status": "finished", "exit_code": poll}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
