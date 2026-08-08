from datetime import datetime, timedelta, timezone

import jwt
from fastapi import WebSocket, status
from passlib.context import CryptContext

from core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
  return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
  return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
  to_encode = data.copy()
  expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
  to_encode.update({"exp": expire})
  return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
  return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


async def authenticate_websocket(websocket: WebSocket, token: str | None) -> int | None:
  """Validates token for WebSockets. Returns user_id if valid, or closes the socket and returns None if invalid."""
  if not token:
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return None

  try:
    payload = decode_access_token(token)
    raw_user_id = payload.get("sub")
    if raw_user_id is None:
      await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
      return None

    return int(raw_user_id)

  except jwt.PyJWTError:
    await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    return None
