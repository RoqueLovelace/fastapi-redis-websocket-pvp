import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

import chat.service as chat_service
import game.service as game_service
import users.service as users_service
from core.security import authenticate_websocket
from ws.manager import manager

router = APIRouter(tags=["ws"])


@router.websocket("/ws/game")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
  user_id = await authenticate_websocket(websocket, token)
  if user_id is None:
    return

  await manager.connect(websocket, user_id)
  await users_service.mark_user_online(user_id)

  try:
    while True:
      data = await websocket.receive_text()
      try:
        payload = json.loads(data)
      except json.JSONDecodeError:
        await websocket.send_text(json.dumps({"error": "Invalid JSON format"}))
        continue

      action = payload.get("action", "chat")

      if action == "chat":
        text = payload.get("text", "").strip()
        if not text:
          continue

        receiver_id = payload.get("receiver_id")
        try:
          await chat_service.send_message(sender_id=user_id, text=text, receiver_id=receiver_id)
        except ValueError as exc:
          await websocket.send_text(json.dumps({"error": str(exc)}))

      elif action == "accept_challenge":
        challenger_id = payload.get("challenger_id")
        if not challenger_id or challenger_id == user_id:
          await websocket.send_text(json.dumps({"error": "Invalid challenger ID"}))
          continue

        try:
          result = await game_service.resolve_challenge(challenger_id=challenger_id, accepter_id=user_id)
        except RuntimeError as exc:
          await websocket.send_text(json.dumps({"error": str(exc)}))
          continue

        if result is None:
          await websocket.send_text(json.dumps({"error": "Challenge no longer exists!"}))

  except WebSocketDisconnect:
    manager.disconnect(user_id)
    await users_service.mark_user_offline(user_id)
