import json
import secrets

from db import record_match as db_record_match
from redis_client import get_redis

CHALLENGES_KEY = "lobby:challenges"
LOBBY_CHANNEL = "channel:game:lobby"


async def create_challenge(user_id: int, username: str, is_heads: bool, stake: int) -> None:
  challenge_data = {
    "user_id": user_id,
    "username": username,
    "is_heads": is_heads,
    "stake": stake,
  }
  await get_redis().hset(CHALLENGES_KEY, str(user_id), json.dumps(challenge_data))


async def remove_challenge(user_id: int) -> None:
  await get_redis().hdel(CHALLENGES_KEY, str(user_id))


async def get_all_challenges() -> list[dict]:
  raw_challenges = await get_redis().hgetall(CHALLENGES_KEY)
  return [json.loads(raw) for raw in raw_challenges.values()]


async def resolve_challenge(challenger_id: int, accepter_id: int) -> dict | None:
  """Flips the coin, records the match, clears the challenge, and publishes the result. Returns the result payload, or None if the challenge no longer exists."""
  challenges = await get_all_challenges()
  challenge = next((c for c in challenges if c["user_id"] == challenger_id), None)
  if not challenge:
    return None

  coin_landed_heads = secrets.randbelow(2) == 0
  challenger_won = challenge["is_heads"] == coin_landed_heads

  winner_id = challenger_id if challenger_won else accepter_id
  loser_id = accepter_id if challenger_won else challenger_id

  match_record = await db_record_match(
    winner_id=winner_id,
    loser_id=loser_id,
    stake=challenge["stake"],
    outcome=coin_landed_heads,
  )

  await remove_challenge(challenger_id)

  result_payload = {
    "type": "game_result",
    "coin_landed_heads": coin_landed_heads,
    "winner_id": winner_id,
    "loser_id": loser_id,
    "stake": challenge["stake"],
    "new_scores": {
      "winner": match_record["winner"]["score"],
      "loser": match_record["loser"]["score"],
    },
  }

  await get_redis().publish(LOBBY_CHANNEL, json.dumps(result_payload))
  return result_payload
