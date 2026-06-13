import asyncio
import json
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

websocket_router = APIRouter()

active_connections: Set[WebSocket] = set()


@websocket_router.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.discard(websocket)


async def broadcast_progress(message: dict):
    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception:
            disconnected.add(connection)
    active_connections.difference_update(disconnected)


def notify_progress(job_id: str, progress: int, status: str, current_item: str = ""):
    """Called from Celery tasks via Redis pub/sub to notify WebSocket clients."""
    from app.core.redis import redis_client
    message = json.dumps({
        "type": "progress",
        "job_id": job_id,
        "progress": progress,
        "status": status,
        "current_item": current_item,
    })
    asyncio.get_event_loop().run_until_complete(
        redis_client.publish("progress_channel", message)
    )
