from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: str
    total_items: int
    processed_items: int
    failed_items: int
    progress_percent: float
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    jobs: list[JobResponse]
    total: int
