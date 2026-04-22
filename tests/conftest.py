"""Test fixtures and configuration."""
import pytest
import os
from httpx import AsyncClient, ASGITransport

os.environ["ENVIRONMENT"] = "development"
os.environ["JWT_SECRET_KEY"] = "test-secret-key"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/oslo_test"

from app.main import app
from app.services.jwt_service import create_access_token
import uuid


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers():
    """Create auth headers with a test JWT."""
    owner_id = uuid.uuid4()
    token = create_access_token(owner_id)
    return {"Authorization": f"Bearer {token}"}, owner_id
