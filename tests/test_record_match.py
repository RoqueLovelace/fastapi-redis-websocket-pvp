from core.security import hash_password
from db.crud import create_user, record_match


async def test_record_match_updates_winner_and_loser_scores():
  winner = await create_user("Winner", hash_password("testpassword123"))
  loser = await create_user("Loser", hash_password("testpassword123"))

  result = await record_match(winner_id=winner["id"], loser_id=loser["id"], stake=50, outcome=True)

  assert result["winner"]["score"] == 550
  assert result["winner"]["streak"] == 1
  assert result["loser"]["score"] == 450
  assert result["loser"]["streak"] == -1
