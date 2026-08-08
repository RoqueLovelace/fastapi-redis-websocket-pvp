import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from .models import Base

load_dotenv()

RAW_DATABASE_URL = os.getenv("DATABASE_URL", "")
if RAW_DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif RAW_DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = RAW_DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = RAW_DATABASE_URL

engine: AsyncEngine | None = None
async_session_maker: async_sessionmaker[AsyncSession] | None = None


async def init_db_pool():
    global engine, async_session_maker
    print("[INFO] Initializing Database Pool...")

    engine = create_async_engine(DATABASE_URL, pool_size=1, max_overflow=9)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.run_sync(Base.metadata.create_all)

    print("[INFO] Database pool initialized.")


async def close_db_pool() -> None:
    global engine
    if engine:
        await engine.dispose()


def get_session_maker() -> async_sessionmaker[AsyncSession]:
    if not async_session_maker:
        raise RuntimeError("[ERROR] There are no connections to the Database")
    return async_session_maker
