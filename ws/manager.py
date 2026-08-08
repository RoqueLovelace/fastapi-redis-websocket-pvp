from fastapi import WebSocket


class ConnectionManager:
  def __init__(self):
    self.active_connections: dict[int, WebSocket] = {}

  async def connect(self, websocket: WebSocket, user_id: int):
    await websocket.accept()
    self.active_connections[user_id] = websocket

  def disconnect(self, user_id: int):
    if user_id in self.active_connections:
      del self.active_connections[user_id]


manager = ConnectionManager()


async def redis_pubsub_listener():
  import redis_client

  if not redis_client.redis_client:
    return

  pubsub = redis_client.redis_client.pubsub()
  await pubsub.psubscribe("channel:*")

  async for message in pubsub.listen():
    if message["type"] == "pmessage":
      channel: str = message["channel"]
      payload_json: str = message["data"]

      if channel == "channel:chat:global":
        for ws in manager.active_connections.values():
          await ws.send_text(payload_json)

      elif channel.startswith("channel:chat:dm_"):
        raw_room_id = channel.replace("channel:chat:", "")
        parts = raw_room_id.split("_")
        if len(parts) == 3:
          try:
            u1, u2 = int(parts[1]), int(parts[2])
            if u1 in manager.active_connections:
              await manager.active_connections[u1].send_text(payload_json)
            if u2 in manager.active_connections:
              await manager.active_connections[u2].send_text(payload_json)
          except ValueError:
            pass

      elif channel == "channel:game:lobby":
        for ws in manager.active_connections.values():
          await ws.send_text(payload_json)
