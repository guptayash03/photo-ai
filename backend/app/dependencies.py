from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.storage import StorageBackend, get_storage


async def get_storage_dep() -> StorageBackend:
    return get_storage()
