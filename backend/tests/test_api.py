import httpx
import pytest

from lego.api.app import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_local_backend_status() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app": "LEGO AI Agent",
        "version": "0.1.0",
    }
