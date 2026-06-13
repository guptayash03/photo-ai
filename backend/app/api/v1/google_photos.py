from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.database import get_db
from app.services.google_photos_service import GooglePhotosService

router = APIRouter()


@router.get("/auth-url")
async def get_auth_url():
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google OAuth not configured")

    service = GooglePhotosService()
    auth_url = service.get_authorization_url()
    return {"auth_url": auth_url}


@router.post("/callback")
async def oauth_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()
    code = body.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code required")

    service = GooglePhotosService()
    tokens = await service.exchange_code(code)
    return {"message": "Google Photos connected successfully", "connected": True}


@router.post("/sync")
async def sync_google_photos(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json() if await request.body() else {}
    access_token = body.get("access_token")

    if not access_token:
        raise HTTPException(status_code=400, detail="Access token required")

    from app.workers.tasks.image_processing import sync_google_photos_task
    sync_google_photos_task.delay(access_token)

    return {"message": "Google Photos sync started", "status": "queued"}


@router.get("/status")
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, func
    from app.models.image import Image

    count_result = await db.execute(
        select(func.count()).select_from(Image).where(Image.source == "google_photos")
    )
    count = count_result.scalar() or 0

    return {
        "connected": count > 0,
        "synced_photos": count,
    }
