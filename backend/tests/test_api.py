"""Test suite for DocuMind API. Run with: pytest tests/ -v"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    await client.post("/api/v1/auth/register", json={"email": "test@example.com", "full_name": "Test User", "password": "testpass123"})
    resp = await client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "testpass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_register_user(client):
    resp = await client.post("/api/v1/auth/register", json={"email": "new@example.com", "full_name": "New User", "password": "password123"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_login_success(client, auth_headers):
    resp = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_documents_empty(client, auth_headers):
    resp = await client.get("/api/v1/documents/", headers=auth_headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_chat_session(client, auth_headers):
    resp = await client.post("/api/v1/chat/sessions", headers=auth_headers, json={"title": "Test"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_llmops_metrics(client, auth_headers):
    resp = await client.get("/api/v1/llmops/metrics/overview", headers=auth_headers)
    assert resp.status_code == 200
    assert "total_calls" in resp.json()
