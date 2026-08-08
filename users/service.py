from core.security import create_access_token
from db import get_or_create_user as db_get_or_create_user
from redis_client import get_redis
from typing import cast

ONLINE_SET_KEY = "users:online"


async def login_or_register(username: str) -> dict:
  user_dict = await db_get_or_create_user(username)
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
