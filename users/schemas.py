from pydantic import BaseModel, Field


class UserLogin(BaseModel):
  username: str
  password: str = Field(min_length=8)


class TokenResponse(BaseModel):
  access_token: str
  token_type: str = "bearer"
  user: dict
