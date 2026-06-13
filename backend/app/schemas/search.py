from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class SearchRequest(BaseModel):
    query: str
    limit: int = 20
    offset: int = 0


class SearchResultItem(BaseModel):
    id: UUID
    original_filename: str
    thumbnail_url: Optional[str] = None
    similarity_score: float
    categories: list[str] = []

    class Config:
        from_attributes = True


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int
