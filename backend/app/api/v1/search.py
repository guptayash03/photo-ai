import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import get_storage
from app.models.image import Image
from app.schemas.search import SearchRequest, SearchResponse, SearchResultItem
from app.ml.embedding_provider import get_embedding_provider

router = APIRouter()


@router.post("", response_model=SearchResponse)
async def search_images(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    provider = get_embedding_provider()
    query_embedding = await provider.embed_text(request.query)

    sql = text("""
        SELECT i.id, i.original_filename, i.thumbnail_path,
               1 - (i.embedding <=> :embedding::vector) as similarity
        FROM images i
        WHERE i.embedding IS NOT NULL
          AND i.processing_status = 'completed'
        ORDER BY i.embedding <=> :embedding::vector
        LIMIT :limit OFFSET :offset
    """)

    result = await db.execute(sql, {
        "embedding": str(query_embedding),
        "limit": request.limit,
        "offset": request.offset,
    })
    rows = result.fetchall()

    storage = get_storage()
    results = []
    for row in rows:
        thumbnail_url = None
        if row.thumbnail_path:
            parts = row.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                thumbnail_url = await storage.get_url(parts[0], parts[1])

        results.append(SearchResultItem(
            id=row.id,
            original_filename=row.original_filename,
            thumbnail_url=thumbnail_url,
            similarity_score=float(row.similarity),
        ))

    return SearchResponse(query=request.query, results=results, total=len(results))


@router.get("/similar/{image_id}", response_model=SearchResponse)
async def find_similar(
    image_id: uuid.UUID,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    image = await db.get(Image, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    if image.embedding is None:
        raise HTTPException(status_code=400, detail="Image has not been processed yet")

    sql = text("""
        SELECT i.id, i.original_filename, i.thumbnail_path,
               1 - (i.embedding <=> :embedding::vector) as similarity
        FROM images i
        WHERE i.id != :image_id
          AND i.embedding IS NOT NULL
        ORDER BY i.embedding <=> :embedding::vector
        LIMIT :limit
    """)

    result = await db.execute(sql, {
        "embedding": str(list(image.embedding)),
        "image_id": str(image_id),
        "limit": limit,
    })
    rows = result.fetchall()

    storage = get_storage()
    results = []
    for row in rows:
        thumbnail_url = None
        if row.thumbnail_path:
            parts = row.thumbnail_path.split("/", 1)
            if len(parts) == 2:
                thumbnail_url = await storage.get_url(parts[0], parts[1])

        results.append(SearchResultItem(
            id=row.id,
            original_filename=row.original_filename,
            thumbnail_url=thumbnail_url,
            similarity_score=float(row.similarity),
        ))

    return SearchResponse(
        query=f"similar to {image.original_filename}",
        results=results,
        total=len(results),
    )
