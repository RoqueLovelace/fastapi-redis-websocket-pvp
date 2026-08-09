import json

from sqlalchemy.exc import IntegrityError

from chat.rooms import get_dm_room_id
from db import save_chat_message as db_save_chat_message
from redis_client import get_redis


async def send_message(sender_id: int, text: str, receiver_id: int | None) -> None:
  room_id = "global" if receiver_id is None else get_dm_room_id(sender_id, receiver_id)

  try:
    msg_uuid = await db_save_chat_message(
      sender_id=sender_id, message=text, room_id=room_id, receiver_id=receiver_id
    )
  except IntegrityError as exc:
    raise ValueError("Recipient does not exist") from exc

  payload = {
    "type": "new_message",
    "public_id": msg_uuid,
    "room_id": room_id,
    "sender_id": sender_id,
    "text": text,
  }

  await get_redis().publish(f"channel:chat:{room_id}", json.dumps(payload))
