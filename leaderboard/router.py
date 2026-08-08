from fastapi import APIRouter

from leaderboard.service import get_leaderboard

router = APIRouter(tags=["leaderboard"])


@router.get("/leaderboard")
async def leaderboard_endpoint():
  source, leaderboard = await get_leaderboard(limit=10, ttl=15)
  return {"source": source, "leaderboard": leaderboard}
