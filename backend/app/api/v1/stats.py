from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.image import Image
from app.models.face import Face, FaceCluster
from app.models.duplicate import DuplicatePair
from app.models.category import ImageCategory
from app.schemas.stats import StatsResponse, CategoryStat

router = APIRouter()


@router.get("/overview", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Total images
    total_result = await db.execute(select(func.count()).select_from(Image))
    total_images = total_result.scalar() or 0

    # Processed count
    processed_result = await db.execute(
        select(func.count()).select_from(Image).where(Image.processing_status == "completed")
    )
    total_processed = processed_result.scalar() or 0

    # Pending count
    pending_result = await db.execute(
        select(func.count()).select_from(Image).where(Image.processing_status == "pending")
    )
    total_pending = pending_result.scalar() or 0

    # Faces and people
    faces_result = await db.execute(select(func.count()).select_from(Face))
    total_faces = faces_result.scalar() or 0

    people_result = await db.execute(
        select(func.count()).select_from(FaceCluster).where(FaceCluster.face_count > 0)
    )
    total_people = people_result.scalar() or 0

    # Duplicates
    dup_result = await db.execute(
        select(func.count()).select_from(DuplicatePair).where(DuplicatePair.status == "pending")
    )
    total_duplicates = dup_result.scalar() or 0

    # Storage used
    storage_result = await db.execute(select(func.sum(Image.file_size)))
    storage_used = storage_result.scalar() or 0

    # Category distribution
    cat_query = (
        select(ImageCategory.category, func.count(ImageCategory.id).label("count"))
        .group_by(ImageCategory.category)
        .order_by(func.count(ImageCategory.id).desc())
    )
    cat_result = await db.execute(cat_query)
    category_distribution = [
        CategoryStat(name=row.category, count=row.count)
        for row in cat_result.all()
    ]

    # Recent uploads (last 24 hours)
    from datetime import datetime, timedelta, timezone
    yesterday = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_result = await db.execute(
        select(func.count()).select_from(Image).where(Image.created_at >= yesterday)
    )
    recent_uploads = recent_result.scalar() or 0

    # Processing queue
    queue_result = await db.execute(
        select(func.count()).select_from(Image).where(
            Image.processing_status.in_(["pending", "processing"])
        )
    )
    processing_queue = queue_result.scalar() or 0

    return StatsResponse(
        total_images=total_images,
        total_processed=total_processed,
        total_pending=total_pending,
        total_faces=total_faces,
        total_people=total_people,
        total_duplicates=total_duplicates,
        storage_used_bytes=storage_used,
        category_distribution=category_distribution,
        recent_uploads_count=recent_uploads,
        processing_queue_size=processing_queue,
    )
