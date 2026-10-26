from httpx import ASGITransport, AsyncClient

from app import __version__
from app.main import app


async def test_health_reports_database_ok() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "version": __version__,
        "demo_mode": True,
    }


async def test_root_opens_the_api_docs() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/")

    assert response.status_code == 307
    assert response.headers["location"] == "/api/docs"


async def test_container_health_endpoint_is_not_in_openapi() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        health = await client.get("/health")
        schema = await client.get("/api/openapi.json")

    assert health.status_code == 200
    assert "/health" not in schema.json()["paths"]
    assert "/api/v1/health" in schema.json()["paths"]
