"""
Shared pytest fixtures for the whole test suite.

Save this as: backend/tests/conftest.py

v3 — the "Event loop is closed" teardown error was coming from setup_db
being a session-scoped ASYNC fixture: by the time the session ends, the
last test's event loop is already closed, so there's nothing to run its
teardown on. Fix: create/drop tables with a plain synchronous engine
instead — no event loop involved at all, so no scope mismatch is possible.
The actual app still talks to the DB through the async engine (with
NullPool) below; the sync engine is only ever used for schema setup/teardown
against the same SQLite file.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.core.database import Base, get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
SYNC_TEST_DATABASE_URL = "sqlite:///./test.db"  # same file, sync driver, setup/teardown only

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
sync_engine = create_engine(SYNC_TEST_DATABASE_URL)


async def override_get_db():
    async with TestSessionLocal() as session:
        yield session
        await session.commit()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Plain sync fixture — no event loop involved, so no teardown scope issue."""
    Base.metadata.create_all(sync_engine)
    yield
    Base.metadata.drop_all(sync_engine)


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
