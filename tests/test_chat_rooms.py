from chat.rooms import get_dm_room_id


def test_dm_room_id_is_order_independent():
  assert get_dm_room_id(1, 2) == get_dm_room_id(2, 1)


def test_dm_room_id_format():
  assert get_dm_room_id(5, 2) == "dm_2_5"
