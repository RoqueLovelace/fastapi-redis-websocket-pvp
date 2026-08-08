from pydantic import BaseModel

class ChallengeCreate(BaseModel):
  user_id: int
  username: str
  is_heads: bool
  stake: int

