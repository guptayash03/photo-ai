import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import get_storage
from app.models.duplicate import DuplicatePair
from app.models.image import Image
from app.schemas.duplicate import (
    DuplicatePairResponse,
    DuplicateListResponse,
    DuplicateResolveRequest,
    DuplicateImageInfo,
)
from app.workers.tasks.duplicate_detection import run_duplicate_scan

router = APIRouter()


@router.get("", response_model=DuplicateListResponse)
async def list_duplicates(
    status: str = Query("pending"),
    duplicate_type: str = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(DuplicatePair).order_by(desc(DuplicatePair.similarity_score))

    if status:
        query = query.where(DuplicatePair.status == status)
    if duplicate_type:
        query = query.where(DuplicatePair.duplicate_type == duplicate_type)

    count_query = select(func.count()).select_from(DuplicatePair)
    if status:
        count_query = count_query.where(DuplicatePair.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    pending_count_result = await db.execute(
        select(func.count()).select_from(DuplicatePair).where(DuplicatePair.status == "pending")
    )
    pending_count = pending_count_result.scalar() or 0

    result = await db.execute(query.offset(offset).limit(limit))
    pairs = result.scalars().all()

    storage = get_storage()
    pair_responses = []
    for pair in pairs:
        image_a = await db.get(Image, pair.image_a_id)
        image_b = await db.get(Image, pair.image_b_id)

        if not image_a or not image_b:
            continue

        thumb_a = None
        thumb_b = None
        if image_a.thumbnail_path:
            parts = image_a.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                thumb_a = await storage.get_url(parts[0], parts[1])
        if image_b.thumbnail_path:
            parts = image_b.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                thumb_b = await storage.get_url(parts[0], parts[1])

        pair_responses.append(DuplicatePairResponse(
            id=pair.id,
            image_a=DuplicateImageInfo(
                id=image_a.id,
                original_filename=image_a.original_filename,
                thumbnail_url=thumb_a,
                file_size=image_a.file_size,
                width=image_a.width,
                height=image_a.height,
            ),
            image_b=DuplicateImageInfo(
                id=image_b.id,
                original_filename=image_b.original_filename,
                thumbnail_url=thumb_b,
                file_size=image_b.file_size,
                width=image_b.width,
                height=image_b.height,
            ),
            similarity_score=pair.similarity_score,
            duplicate_type=pair.duplicate_type,
            detection_method=pair.detection_method,
            status=pair.status,
            created_at=pair.created_at,
        ))

    return DuplicateListResponse(pairs=pair_responses, total=total, pending_count=pending_count)


@router.post("/{pair_id}/resolve")
async def resolve_duplicate(
    pair_id: uuid.UUID,
    request: DuplicateResolveRequest,
    db: AsyncSession = Depends(get_db),
):
    pair = await db.get(DuplicatePair, pair_id)
    if not pair:
        raise HTTPException(status_code=404, detail="Duplicate pair not found")

    valid_actions = {"keep_a", "keep_b", "keep_both", "dismiss"}
    if request.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Must be one of: {valid_actions}")

    if request.action == "keep_a":
        image_b = await db.get(Image, pair.image_b_id)
        if image_b:
            storage = get_storage()
            parts = image_b.storage_path.split("/", 1)
            if len(parts) == 2:
                await storage.delete(parts[0], parts[1])
            await db.delete(image_b)
        pair.status = "resolved_keep_a"
    elif request.action == "keep_b":
        image_a = await db.get(Image, pair.image_a_id)
        if image_a:
            storage = get_storage()
            parts = image_a.storage_path.split("/", 1)
            if len(parts) == 2:
                await storage.delete(parts[0], parts[1])
            await db.delete(image_a)
        pair.status = "resolved_keep_b"
    elif request.action == "keep_both":
        pair.status = "resolved_keep_both"
    elif request.action == "dismiss":
        pair.status = "dismissed"

    await db.commit()
    return {"message": f"Duplicate resolved: {request.action}"}


@router.post("/scan")
async def trigger_duplicate_scan(db: AsyncSession = Depends(get_db)):
    run_duplicate_scan.delay()
    return {"message": "Duplicate scan started", "status": "queued"}
