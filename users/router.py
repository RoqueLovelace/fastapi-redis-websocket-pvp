from fastapi import APIRouter, HTTPException, Request, status

from core.rate_limit import enforce_rate_limit
from users.schemas import TokenResponse, UserLogin
from users.service import InvalidCredentialsError, login_or_register

router = APIRouter(tags=["users"])


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin, request: Request):
  client_ip = request.client.host if request.client else "unknown"
  await enforce_rate_limit(f"ratelimit:login:{client_ip}", limit=5, window_seconds=60)

  try:
    return await login_or_register(user_data.username, user_data.password)
  except InvalidCredentialsError:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
