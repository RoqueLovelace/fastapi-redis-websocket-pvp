from fastapi import HTTPException, status

from redis_client import get_redis


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> bool:
  """Returns True if this call is allowed, False if the key has already hit limit calls within window_seconds. Uses a fixed-window counter: the first call in a window sets the expiry, every call after just increments."""
  redis = get_redis()
  current = await redis.incr(key)
  if current == 1:
    await redis.expire(key, window_seconds)
  return current <= limit


async def enforce_rate_limit(key: str, limit: int, window_seconds: int) -> None:
  """Raises a 429 HTTPException if the key has exceeded limit calls within window_seconds. For HTTP routes only - websocket handlers should call check_rate_limit directly and reply in-band instead."""
  allowed = await check_rate_limit(key, limit, window_seconds)
  if not allowed:
    raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many requests, slow down.")
