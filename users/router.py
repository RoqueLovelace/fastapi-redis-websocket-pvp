from fastapi import APIRouter, Request

from core.rate_limit import enforce_rate_limit
from users.schemas import TokenResponse, UserLogin
from users.service import login_or_register

router = APIRouter(tags=["users"])


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
  client_ip = request.client.host if request.client else "unknown"
  await enforce_rate_limit(f"ratelimit:login:{client_ip}", limit=5, window_seconds=60)
  return await login_or_register(user_data.username)
