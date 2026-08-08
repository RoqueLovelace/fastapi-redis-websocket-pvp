from fastapi import APIRouter

from users.schemas import TokenResponse, UserLogin
from users.service import login_or_register

router = APIRouter(tags=["users"])


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
  return await login_or_register(user_data.username)
