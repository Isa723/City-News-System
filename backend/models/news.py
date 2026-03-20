from pydantic import BaseModel, Field
from typing import List, Optional, Literal

Category = Literal[
    "Trafik Kazası",
    "Yangın",
    "Elektrik Kesintisi",
    "Hırsızlık",
    "Kültürel Etkinlikler",
    "Diğer",
]


class SourceItem(BaseModel):
    name: str
    url: str


class NewsItem(BaseModel):
    # Mongo id (stringified) for API responses
    id: Optional[str] = Field(default=None, alias="_id")

    # Mandatory fields from PDF
    category: Category
    title: str
    content: str
    publish_date: str
    sources: List[SourceItem]

    # Location extraction + geocoding
    location_text: str
    district: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    # Demo/debug visibility for extracted mentions (PDF §6)
    location_candidates: List[str] = Field(default_factory=list)

    class Config:
        populate_by_name = True
