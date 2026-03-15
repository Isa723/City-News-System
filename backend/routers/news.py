from fastapi import APIRouter
from typing import List

router = APIRouter()

@router.get("/api/news")
async def get_news():
    return []
