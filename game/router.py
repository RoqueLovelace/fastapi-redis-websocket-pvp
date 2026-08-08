from fastapi import APIRouter

from game.schemas import ChallengeCreate
from game.service import create_challenge, get_all_challenges, remove_challenge

router = APIRouter(prefix="/lobby", tags=["game"])


@router.get("")
async def get_lobby():
  challenges = await get_all_challenges()
  return {"challenges": challenges}


@router.post("/challenge")
async def post_challenge(challenge: ChallengeCreate):
  await create_challenge(
    user_id=challenge.user_id,
    username=challenge.username,
    is_heads=challenge.is_heads,
    stake=challenge.stake,
  )
  return {"message": "Challenge posted"}


@router.delete("/challenge/{user_id}")
async def cancel_challenge(user_id: int):
  await remove_challenge(user_id)
  return {"message": "Challenge removed"}
