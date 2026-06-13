import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.storage import get_storage
from app.models.face import Face, FaceCluster
from app.models.image import Image
from app.schemas.face import (
    FaceClusterResponse,
    FaceClusterListResponse,
    FaceClusterUpdateRequest,
    FaceMergeRequest,
)
from app.schemas.image import ImageResponse

router = APIRouter()


@router.get("/clusters", response_model=FaceClusterListResponse)
async def list_face_clusters(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(FaceCluster)
        .where(FaceCluster.face_count > 0)
        .order_by(desc(FaceCluster.face_count))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    clusters = result.scalars().all()

    count_result = await db.execute(
        select(func.count()).select_from(FaceCluster).where(FaceCluster.face_count > 0)
    )
    total = count_result.scalar() or 0

    storage = get_storage()
    cluster_responses = []
    for cluster in clusters:
        thumbnail_url = None
        if cluster.representative_face_id:
            face = await db.get(Face, cluster.representative_face_id)
            if face and face.thumbnail_path:
                parts = face.thumbnail_path.split("/", 1)
                if len(parts) == 2:
                    thumbnail_url = await storage.get_url(parts[0], parts[1])

        cluster_responses.append(FaceClusterResponse(
            id=cluster.id,
            name=cluster.name,
            face_count=cluster.face_count,
            representative_thumbnail_url=thumbnail_url,
            created_at=cluster.created_at,
        ))

    return FaceClusterListResponse(clusters=cluster_responses, total=total)


@router.get("/clusters/{cluster_id}/images", response_model=dict)
async def get_cluster_images(
    cluster_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    cluster = await db.get(FaceCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Face cluster not found")

    query = (
        select(Image)
        .join(Face, Face.image_id == Image.id)
        .where(Face.cluster_id == cluster_id)
        .distinct()
        .order_by(desc(Image.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    images = result.scalars().all()

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
            created_at=img.created_at,
        ))

    return {
        "cluster": FaceClusterResponse(
            id=cluster.id,
            name=cluster.name,
            face_count=cluster.face_count,
            created_at=cluster.created_at,
        ),
        "images": image_responses,
        "total": cluster.face_count,
    }


@router.patch("/clusters/{cluster_id}", response_model=FaceClusterResponse)
async def update_cluster(
    cluster_id: uuid.UUID,
    request: FaceClusterUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    cluster = await db.get(FaceCluster, cluster_id)
    if not cluster:
        raise HTTPException(status_code=404, detail="Face cluster not found")

    if request.name is not None:
        cluster.name = request.name

    await db.commit()
    await db.refresh(cluster)

    return FaceClusterResponse(
        id=cluster.id,
        name=cluster.name,
        face_count=cluster.face_count,
        created_at=cluster.created_at,
    )


@router.post("/clusters/merge")
async def merge_clusters(
    request: FaceMergeRequest,
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(FaceCluster, request.source_cluster_id)
    target = await db.get(FaceCluster, request.target_cluster_id)

    if not source or not target:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Move all faces from source to target
    faces_query = select(Face).where(Face.cluster_id == source.id)
    result = await db.execute(faces_query)
    faces = result.scalars().all()

    for face in faces:
        face.cluster_id = target.id

    target.face_count += source.face_count
    source.face_count = 0

    await db.delete(source)
    await db.commit()

    return {"message": "Clusters merged successfully", "target_cluster_id": str(target.id)}
