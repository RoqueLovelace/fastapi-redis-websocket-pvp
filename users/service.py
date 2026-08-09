from typing import cast

from core.security import create_access_token, hash_password, verify_password
from db import create_user as db_create_user
from db import get_user_by_username as db_get_user_by_username
from redis_client import get_redis

ONLINE_SET_KEY = "users:online"


class InvalidCredentialsError(Exception):
  pass


async def login_or_register(username: str, password: str) -> dict:
  """Logs in an existing user after verifying their password, or registers a new one with the given username and password if it doesn't exist yet - same combined flow the endpoint always had, now with password verification added."""
  existing = await db_get_user_by_username(username)

  if existing:
    if not verify_password(password, existing["password_hash"]):
      raise InvalidCredentialsError("Invalid username or password")
    existing.pop("password_hash")
    user_dict = existing
  else:
    user_dict = await db_create_user(username, hash_password(password))

  user_dict["public_id"] = str(user_dict["public_id"])
  token = create_access_token(data={"sub": str(user_dict["id"]), "username": user_dict["username"]})

  return {
    "access_token": token,
    "token_type": "bearer",
    "user": user_dict,
  }


async def mark_user_online(user_id: int) -> None:
  await get_redis().sadd(ONLINE_SET_KEY, str(user_id))


async def mark_user_offline(user_id: int) -> None:
  await get_redis().srem(ONLINE_SET_KEY, str(user_id))


async def get_online_users() -> set[str]:
  online_users = cast(set[str], await get_redis().smembers(ONLINE_SET_KEY))
  return online_users
