from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class DuplicateImageInfo(BaseModel):
    id: UUID
    original_filename: str
    thumbnail_url: Optional[str] = None
    file_size: int
    width: Optional[int] = None
    height: Optional[int] = None


class DuplicatePairResponse(BaseModel):
    id: UUID
    image_a: DuplicateImageInfo
    image_b: DuplicateImageInfo
    similarity_score: float
    duplicate_type: str
    detection_method: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class DuplicateListResponse(BaseModel):
    pairs: list[DuplicatePairResponse]
    total: int
    pending_count: int


class DuplicateResolveRequest(BaseModel):
    action: str  # "keep_a", "keep_b", "keep_both", "dismiss"
