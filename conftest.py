import fakeredis.aioredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from typing import cast

from sqlalchemy.ext.asyncio.engine import AsyncEngine

import db.session as db_session
import redis_client
from db.models import Base
from db.session import close_db_pool, init_db_pool
from main import app


@pytest_asyncio.fixture(scope="session", autouse=True)
async def db_pool():
  await init_db_pool()
  yield
  await close_db_pool()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables(db_pool):
  yield
  engine = cast(AsyncEngine, db_session.engine)
  async with engine.begin() as conn:
    for table in reversed(Base.metadata.sorted_tables):
      await conn.execute(table.delete())


@pytest_asyncio.fixture
async def fake_redis():
  fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
  redis_client.redis_client = fake
  yield fake
  await fake.aclose()
  redis_client.redis_client = None


@pytest_asyncio.fixture
async def client():
  transport = ASGITransport(app=app)
  async with AsyncClient(transport=transport, base_url="http://test") as ac:
    yield ac
