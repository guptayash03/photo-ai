import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import get_storage
from app.models.image import Image
from app.models.category import ImageCategory
from app.schemas.image import (
    ImageResponse,
    ImageListResponse,
    ImageUploadResponse,
    BatchUploadResponse,
    ImageDetailResponse,
)
from app.workers.tasks.image_processing import process_image_pipeline

router = APIRouter()


@router.post("/upload", response_model=BatchUploadResponse)
async def upload_images(
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
):
    storage = get_storage()
    uploaded = []
    failed = 0

    for file in files:
        try:
            content = await file.read()
            image_id = uuid.uuid4()
            key = f"{image_id}/{file.filename}"

            await storage.upload("photos", key, content, content_type=file.content_type or "image/jpeg")

            image = Image(
                id=image_id,
                original_filename=file.filename,
                storage_path=f"photos/{key}",
                file_size=len(content),
                mime_type=file.content_type or "image/jpeg",
                source="upload",
                processing_status="pending",
            )
            db.add(image)
            await db.flush()

            process_image_pipeline.delay(str(image_id))

            uploaded.append(ImageUploadResponse(
                id=image_id,
                filename=file.filename,
                status="processing",
                message="Image uploaded and queued for processing",
            ))
        except Exception as e:
            failed += 1
            uploaded.append(ImageUploadResponse(
                id=uuid.uuid4(),
                filename=file.filename or "unknown",
                status="failed",
                message=str(e),
            ))

    await db.commit()
    return BatchUploadResponse(uploaded=uploaded, total=len(files), failed=failed)


@router.get("", response_model=ImageListResponse)
async def list_images(
    cursor: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Image).order_by(desc(Image.created_at))

    if cursor:
        try:
            cursor_id = uuid.UUID(cursor)
            cursor_image = await db.get(Image, cursor_id)
            if cursor_image:
                query = query.where(Image.created_at < cursor_image.created_at)
        except ValueError:
            pass

    if source:
        query = query.where(Image.source == source)
    if status:
        query = query.where(Image.processing_status == status)
    if category:
        query = query.join(ImageCategory).where(ImageCategory.category == category)

    count_query = select(func.count()).select_from(Image)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    result = await db.execute(query.limit(limit))
    images = result.scalars().all()

    storage = get_storage()
    image_responses = []
    for img in images:
        thumbnail_url = None
        if img.thumbnail_path:
            parts = img.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                thumbnail_url = await storage.get_url(parts[0], parts[1])

        cats = [c.category for c in img.categories] if img.categories else []
        image_responses.append(ImageResponse(
            id=img.id,
            original_filename=img.original_filename,
            thumbnail_url=thumbnail_url,
            file_size=img.file_size,
            mime_type=img.mime_type,
            width=img.width,
            height=img.height,
            taken_at=img.taken_at,
            camera_make=img.camera_make,
            camera_model=img.camera_model,
            gps_latitude=img.gps_latitude,
            gps_longitude=img.gps_longitude,
            source=img.source,
            processing_status=img.processing_status,
            categories=cats,
            created_at=img.created_at,
        ))

    next_cursor = str(images[-1].id) if len(images) == limit else None
    return ImageListResponse(images=image_responses, total=total, next_cursor=next_cursor)


@router.get("/{image_id}", response_model=ImageDetailResponse)
async def get_image(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    image = await db.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    storage = get_storage()
    thumbnail_url = None
    storage_url = None

    if image.thumbnail_path:
        parts = image.thumbnail_path.split("/", 1)
        if len(parts) == 2:
            thumbnail_url = await storage.get_url(parts[0], parts[1])

    parts = image.storage_path.split("/", 1)
    if len(parts) == 2:
        storage_url = await storage.get_url(parts[0], parts[1])

    cats = [c.category for c in image.categories] if image.categories else []
    face_count = len(image.faces) if image.faces else 0

    return ImageDetailResponse(
        id=image.id,
        original_filename=image.original_filename,
        thumbnail_url=thumbnail_url,
        storage_url=storage_url,
        file_size=image.file_size,
        mime_type=image.mime_type,
        width=image.width,
        height=image.height,
        taken_at=image.taken_at,
        camera_make=image.camera_make,
        camera_model=image.camera_model,
        gps_latitude=image.gps_latitude,
        gps_longitude=image.gps_longitude,
        source=image.source,
        processing_status=image.processing_status,
        categories=cats,
        created_at=image.created_at,
        phash=image.phash,
        face_count=face_count,
    )


@router.delete("/{image_id}")
async def delete_image(image_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    image = await db.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    storage = get_storage()
    try:
        parts = image.storage_path.split("/", 1)
        if len(parts) == 2:
            await storage.delete(parts[0], parts[1])
        if image.thumbnail_path:
            parts = image.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                await storage.delete(parts[0], parts[1])
    except Exception:
        pass

    await db.delete(image)
    await db.commit()
    return {"message": "Image deleted successfully"}
