from pydantic import BaseModel


class UserLogin(BaseModel):
  username: str


class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"
  user: dict
