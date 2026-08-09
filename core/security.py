from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from fastapi import WebSocket, status

from core.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    pwd_bytes = plain_password.encode("utf-8")[:72]
    hash_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(pwd_bytes, hash_bytes)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


async def authenticate_websocket(websocket: WebSocket, token: str | None) -> int | None:
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
