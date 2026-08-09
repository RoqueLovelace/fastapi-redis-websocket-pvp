import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
  DATABASE_URL: str = os.getenv("DATABASE_URL", "")
  REDIS_URL: str = os.getenv("REDIS_URL", "")
  JWT_SECRET: str = os.getenv("JWT_SECRET") or "super-secret-key-change-tho-it-also-has-to-be-long-tho-123456"
  JWT_ALGORITHM: str = "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
  LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
