import io
import pytest
from PIL import Image
from httpx import AsyncClient, ASGITransport

from app.main import app


def _create_test_image() -> bytes:
    img = Image.new("RGB", (200, 200), (255, 100, 50))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_health_check():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_stats():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert "total_images" in data
        assert "total_people" in data


@pytest.mark.asyncio
async def test_list_images_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/images")
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert "total" in data


@pytest.mark.asyncio
async def test_list_categories():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data


@pytest.mark.asyncio
async def test_search_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/search", json={"query": "sunset", "limit": 10})
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "sunset"
        assert "results" in data


@pytest.mark.asyncio
async def test_list_face_clusters():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/faces/clusters")
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data


@pytest.mark.asyncio
async def test_list_duplicates():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/duplicates?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert "pairs" in data


@pytest.mark.asyncio
async def test_get_nonexistent_image():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/images/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404
