def get_dm_room_id(user1_id: int, user2_id: int) -> str:
  first, second = sorted([user1_id, user2_id])
  return f"dm_{first}_{second}"
