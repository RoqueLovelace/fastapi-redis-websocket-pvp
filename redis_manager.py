import os
import json
import redis.asyncio as redis
from dotenv import load_dotenv
from typing import cast

load_dotenv()
REDIS_URL = str(os.getenv("REDIS_URL"))

redis_client: redis.Redis | None = None


async def init_redis_pool():
  global redis_client
  print("[INFO] Initializing Redis Pool...")
  redis_client = redis.from_url(REDIS_URL, decode_responses=True)

async def close_redis_pool():
  global redis_client
  if redis_client:
    await redis_client.aclose()
    print("[INFO] Redis pool closed...")


async def mark_user_online(user_id: int) -> None:
  if not redis_client: 
    return
  await redis_client.sadd("users:online", str(user_id))
  

async def mark_user_offline(user_id: int) -> None:
  if not redis_client: 
    return
  await redis_client.srem("users:online", str(user_id))

async def get_online_users() -> set[str]:
  if not redis_client:
    return set()
  raw_set = await redis_client.smembers("users:online")
  return cast(set[str], raw_set)


async def create_challenge(user_id: int, username: str, is_heads: bool, stake: int) -> None:
  if not redis_client:
    return
  challenge_data = {
    "user_id": user_id,
    "username": username,
    "is_heads": is_heads,
    "stake": stake
  }


  await redis_client.hset(
    "lobby:challenges",
    str(user_id),
    json.dumps(challenge_data)
  )

async def remove_challenge(user_id: int) -> None:
  if not redis_client:
    return

  await redis_client.hdel("lobby:challenges", str(user_id))

async def get_all_challenges() -> list[dict]:
  if not redis_client:
    return []

  raw_challenges = await redis_client.hgetall("lobby:challenges")

  challenges = []
  for raw_json_string in raw_challenges.values():
    challenges.append(json.loads(raw_json_string))

  return challenges


async def publish_chat_message(room_id: str, sender_id: int, message_uuid: str, text: str) -> None:
    if not redis_client:
        return
    
    payload = {
        "type": "new_message",
        "public_id": message_uuid,
        "room_id": room_id,
        "sender_id": sender_id,
        "text": text
    }
    
    channel_name = f"channel:chat:{room_id}"
    await redis_client.publish(channel_name, json.dumps(payload))


async def publish_game_result(result_payload: dict) -> None:
    if not redis_client:
        return
    
    await redis_client.publish("channel:game:lobby", json.dumps(result_payload))

async def cache_leaderboard(leaderboard_data: list[dict], ttl: int = 15) -> None:
    if not redis_client:
        return
    await redis_client.set("cache:leaderboard", json.dumps(leaderboard_data), ex=ttl)


async def get_cached_leaderboard() -> list[dict] | None:
    if not redis_client:
        return None
    cached = await redis_client.get("cache:leaderboard")
    if cached:
        return json.loads(cached)
    return None
