import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
  AsyncEngine,
  AsyncSession,
  async_sessionmaker,
  create_async_engine,
)

from core.config import settings

from .models import Base

logger = logging.getLogger(__name__)

_raw_url = settings.DATABASE_URL
if _raw_url.startswith("postgresql://"):
  DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
  DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
  DATABASE_URL = _raw_url

engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db_pool():
  global engine, async_session_maker
  logger.info("Initializing database pool")

  engine = create_async_engine(DATABASE_URL, pool_size=1, max_overflow=9)
  async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

  async with engine.begin() as conn:
    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
    await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
    await conn.run_sync(Base.metadata.create_all)

  logger.info("Database pool initialized")


async def close_db_pool() -> None:
  global engine
  if engine:
    await engine.dispose()


def get_session_maker() -> async_sessionmaker[AsyncSession]:
  if not async_session_maker:
    raise RuntimeError("[ERROR] There are no connections to the Database")
  return async_session_maker
