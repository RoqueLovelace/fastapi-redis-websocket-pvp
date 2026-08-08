from game.service import create_challenge, get_all_challenges, remove_challenge


async def test_create_and_fetch_challenge(fake_redis):
  await create_challenge(user_id=1, username="Bob", is_heads=True, stake=100)

  challenges = await get_all_challenges()
  assert len(challenges) == 1
  assert challenges[0]["username"] == "Bob"
  assert challenges[0]["stake"] == 100

  await remove_challenge(user_id=1)
  challenges_after_delete = await get_all_challenges()
  assert len(challenges_after_delete) == 0
