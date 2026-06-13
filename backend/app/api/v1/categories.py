from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import get_storage
from app.models.image import Image
from app.models.category import ImageCategory
from app.schemas.category import CategoryResponse, CategoryListResponse
from app.schemas.image import ImageResponse, ImageListResponse

router = APIRouter()

VALID_CATEGORIES = [
    "document", "prescription", "receipt", "people",
    "travel", "pet", "food", "nature", "other"
]


@router.get("", response_model=CategoryListResponse)
async def list_categories(db: AsyncSession = Depends(get_db)):
    query = (
        select(ImageCategory.category, func.count(ImageCategory.id).label("count"))
        .group_by(ImageCategory.category)
        .order_by(desc("count"))
    )
    result = await db.execute(query)
    rows = result.all()

    total_result = await db.execute(select(func.count()).select_from(Image))
    total_images = total_result.scalar() or 0

    storage = get_storage()
    categories = []
    for row in rows:
        # Get sample thumbnails for each category
        sample_query = (
            select(Image.thumbnail_path)
            .join(ImageCategory)
            .where(ImageCategory.category == row.category)
            .where(Image.thumbnail_path.isnot(None))
            .limit(4)
        )
        sample_result = await db.execute(sample_query)
        sample_paths = sample_result.scalars().all()

        sample_urls = []
        for path in sample_paths:
            if path:
                parts = path.split("/", 1)
                if len(parts) == 2:
                    url = await storage.get_url(parts[0], parts[1])
                    sample_urls.append(url)

        categories.append(CategoryResponse(
            name=row.category,
            count=row.count,
            sample_thumbnail_urls=sample_urls,
        ))

    return CategoryListResponse(categories=categories, total_images=total_images)


@router.get("/{category}/images", response_model=ImageListResponse)
async def get_category_images(
    category: str,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Image)
        .join(ImageCategory)
        .where(ImageCategory.category == category)
        .order_by(desc(Image.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    images = result.scalars().all()

    count_query = (
        select(func.count())
        .select_from(Image)
        .join(ImageCategory)
        .where(ImageCategory.category == category)
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    storage = get_storage()
    image_responses = []
    for img in images:
        thumbnail_url = None
        if img.thumbnail_path:
            parts = img.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                thumbnail_url = await storage.get_url(parts[0], parts[1])

        image_responses.append(ImageResponse(
            id=img.id,
            original_filename=img.original_filename,
            thumbnail_url=thumbnail_url,
            file_size=img.file_size,
            mime_type=img.mime_type,
            width=img.width,
            height=img.height,
            source=img.source,
            processing_status=img.processing_status,
            categories=[category],
            created_at=img.created_at,
        ))

    return ImageListResponse(images=image_responses, total=total, next_cursor=None)
