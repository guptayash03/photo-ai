from pydantic import BaseModel


class CategoryStat(BaseModel):
    name: str
    count: int


class StatsResponse(BaseModel):
    total_images: int
    total_processed: int
    total_pending: int
    total_faces: int
    total_people: int
    total_duplicates: int
    storage_used_bytes: int
    category_distribution: list[CategoryStat]
    recent_uploads_count: int
    processing_queue_size: int
