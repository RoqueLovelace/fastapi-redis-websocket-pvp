from db.crud import get_or_create_user, record_match


async def test_record_match_updates_winner_and_loser_scores():
  winner = await get_or_create_user("Winner")
  loser = await get_or_create_user("Loser")

  result = await record_match(winner_id=winner["id"], loser_id=loser["id"], stake=50, outcome=True)

  assert result["winner"]["score"] == 550
  assert result["winner"]["streak"] == 1
  assert result["loser"]["score"] == 450
  assert result["loser"]["streak"] == -1
