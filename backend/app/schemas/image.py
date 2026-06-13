from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class ImageResponse(BaseModel):
    id: UUID
    original_filename: str
    thumbnail_url: Optional[str] = None
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    taken_at: Optional[datetime] = None
    camera_make: Optional[str] = None
    camera_model: Optional[str] = None
    gps_latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    source: str
    processing_status: str
    categories: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class ImageDetailResponse(ImageResponse):
    storage_url: Optional[str] = None
    phash: Optional[str] = None
    face_count: int = 0
    similar_images: list["ImageResponse"] = []


class ImageListResponse(BaseModel):
    images: list[ImageResponse]
    total: int
    next_cursor: Optional[str] = None


class ImageUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    message: str


class BatchUploadResponse(BaseModel):
    uploaded: list[ImageUploadResponse]
    total: int
    failed: int
