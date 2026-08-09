from core.rate_limit import check_rate_limit


async def test_allows_calls_under_the_limit(fake_redis):
  for _ in range(3):
    assert await check_rate_limit("ratelimit:test:under", limit=3, window_seconds=10) is True


async def test_blocks_calls_over_the_limit(fake_redis):
  for _ in range(3):
    await check_rate_limit("ratelimit:test:over", limit=3, window_seconds=10)

  assert await check_rate_limit("ratelimit:test:over", limit=3, window_seconds=10) is False


async def test_different_keys_have_independent_limits(fake_redis):
  for _ in range(3):
    await check_rate_limit("ratelimit:test:key_a", limit=3, window_seconds=10)

  assert await check_rate_limit("ratelimit:test:key_b", limit=3, window_seconds=10) is True
