from db.crud import calculate_streak_multiplier


def test_streak_multiplier_zero():
  assert calculate_streak_multiplier(0) == 1


def test_streak_multiplier_winning_streak():
  assert calculate_streak_multiplier(3) == 3


def test_streak_multiplier_losing_streak():
  assert calculate_streak_multiplier(-4) == 4
