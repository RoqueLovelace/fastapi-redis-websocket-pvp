import json

from db import get_top_leaderboard as db_get_top_leaderboard
from redis_client import get_redis

CACHE_KEY = "cache:leaderboard"


async def get_leaderboard(limit: int = 10, ttl: int = 15) -> tuple[str, list[dict]]:
  cached = await get_redis().get(CACHE_KEY)
  if cached is not None:
    return "cache", json.loads(cached)

  leaderboard = await db_get_top_leaderboard(limit=limit)
  await get_redis().set(CACHE_KEY, json.dumps(leaderboard), ex=ttl)
  return "database", leaderboard
