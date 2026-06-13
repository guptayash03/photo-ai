from pydantic import BaseModel


class CategoryResponse(BaseModel):
    name: str
    count: int
    sample_thumbnail_urls: list[str] = []


class CategoryListResponse(BaseModel):
    categories: list[CategoryResponse]
    total_images: int
