import logging

import redis.asyncio as redis

from core.config import settings

logger = logging.getLogger(__name__)

redis_client: redis.Redis | None = None


async def init_redis_pool() -> None:
  global redis_client
  logger.info("Initializing Redis pool")
  redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis_pool() -> None:
  global redis_client
  if redis_client:
    await redis_client.aclose()
    logger.info("Redis pool closed")


def get_redis() -> redis.Redis:
  if not redis_client:
    raise RuntimeError("[ERROR] There are no connections to Redis")
  return redis_client
