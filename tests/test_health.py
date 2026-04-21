"""Health endpoint tests."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns 200 with expected fields."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "ai_service_status" in data
