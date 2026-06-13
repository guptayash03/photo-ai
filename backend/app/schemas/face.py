from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class FaceClusterResponse(BaseModel):
    id: UUID
    name: Optional[str] = None
    face_count: int
    representative_thumbnail_url: Optional[str] = None
    sample_image_urls: list[str] = []
    created_at: datetime

    class Config:
        from_attributes = True


class FaceClusterListResponse(BaseModel):
    clusters: list[FaceClusterResponse]
    total: int


class FaceClusterUpdateRequest(BaseModel):
    name: Optional[str] = None


class FaceMergeRequest(BaseModel):
    source_cluster_id: UUID
    target_cluster_id: UUID
