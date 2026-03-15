from pydantic import BaseModel, Field
from typing import Optional

class NewsItem(BaseModel):
    title: str
    content: str
    category: str
    location_text: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    publish_date: str
    source: str
    url: str
