from fastapi import APIRouter

from app.api.v1 import images, search, faces, duplicates, categories, google_photos, jobs, stats

api_router = APIRouter()

api_router.include_router(images.router, prefix="/images", tags=["Images"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(faces.router, prefix="/faces", tags=["Faces"])
api_router.include_router(duplicates.router, prefix="/duplicates", tags=["Duplicates"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(google_photos.router, prefix="/google-photos", tags=["Google Photos"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Jobs"])
api_router.include_router(stats.router, prefix="/stats", tags=["Stats"])
