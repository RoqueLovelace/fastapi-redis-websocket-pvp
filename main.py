import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, Query, status
from pydantic import BaseModel
from typing import cast
import secrets
import jwt
from fastapi.responses import HTMLResponse
import os

import db as database
import redis_manager
import chat_manager
import auth
from fastapi.middleware.cors import CORSMiddleware


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
    if not redis_manager.redis_client:
        return
    
    pubsub = redis_manager.redis_client.pubsub()
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.init_db_pool()
    await redis_manager.init_redis_pool()
    
    listener_task = asyncio.create_task(redis_pubsub_listener())
    print("[SERVER] FastAPI is ready to accept connections!")
    
    yield
    
    listener_task.cancel()
    await redis_manager.close_redis_pool()
    await database.close_db_pool()
    print("[SERVER] FastAPI shut down safely.")

app = FastAPI(lifespan=lifespan, title="Coin Flip PvP API")

class UserLogin(BaseModel):
    username: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict

class ChallengeCreate(BaseModel):
    user_id: int
    username: str
    is_heads: bool
    stake: int

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html not found</h1>"

@app.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    user_dict = await database.get_or_create_user(user_data.username)
    user_dict["public_id"] = str(user_dict["public_id"])
    
    token = auth.create_access_token(
        data={"sub": str(user_dict["id"]), "username": user_dict["username"]}
    )
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": user_dict
    }

@app.get("/lobby")
async def get_lobby():
    challenges = await redis_manager.get_all_challenges()
    return {"challenges": challenges}


@app.post("/lobby/challenge")
async def post_challenge(challenge: ChallengeCreate):
    await redis_manager.create_challenge(
        user_id=challenge.user_id,
        username=challenge.username,
        is_heads=challenge.is_heads,
        stake=challenge.stake
    )
    return {"message": "Challenge posted"}


@app.delete("/lobby/challenge/{user_id}")
async def cancel_challenge(user_id: int):
    await redis_manager.remove_challenge(user_id)
    return {"message": "Challenge removed"}

@app.websocket("/ws/game")
async def websocket_endpoint(
    websocket: WebSocket, 
    token: str = Query(None)
):
    user_id = await auth.authenticate_websocket(websocket, token)
    if user_id is None:
        return 
    await manager.connect(websocket, user_id)
    await redis_manager.mark_user_online(user_id)
    
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
                room_id = "global" if receiver_id is None else chat_manager.get_dm_room_id(user_id, receiver_id)
                
                msg_uuid = await database.save_chat_message(
                    sender_id=user_id, message=text, room_id=room_id, receiver_id=receiver_id
                )
                
                await redis_manager.publish_chat_message(
                    room_id=room_id, sender_id=user_id, message_uuid=msg_uuid, text=text
                )

            elif action == "accept_challenge":
                challenger_id = payload.get("challenger_id")
                if not challenger_id or challenger_id == user_id:
                    await websocket.send_text(json.dumps({"error": "Invalid challenger ID"}))
                    continue
                
                challenges = await redis_manager.get_all_challenges()
                challenge = next((c for c in challenges if c["user_id"] == challenger_id), None)
                
                if not challenge:
                    await websocket.send_text(json.dumps({"error": "Challenge no longer exists!"}))
                    continue
                
                coin_landed_heads = secrets.randbelow(2) == 0
                challenger_won = (challenge["is_heads"] == coin_landed_heads)
                
                winner_id = challenger_id if challenger_won else user_id
                loser_id = user_id if challenger_won else challenger_id
                
                match_record = await database.record_match(
                    winner_id=winner_id,
                    loser_id=loser_id,
                    stake=challenge["stake"],
                    outcome=coin_landed_heads
                )
                
                await redis_manager.remove_challenge(challenger_id)
                
                result_payload = {
                    "type": "game_result",
                    "coin_landed_heads": coin_landed_heads,
                    "winner_id": winner_id,
                    "loser_id": loser_id,
                    "stake": challenge["stake"],
                    "new_scores": {
                        "winner": match_record["winner"]["score"],
                        "loser": match_record["loser"]["score"]
                    }
                }
                
                await redis_manager.publish_game_result(result_payload) 

    except WebSocketDisconnect:
        manager.disconnect(user_id)
        await redis_manager.mark_user_offline(user_id)


@app.get("/leaderboard")
async def get_leaderboard():
    cached_data = await redis_manager.get_cached_leaderboard()
    if cached_data is not None:
        return {"source": "cache", "leaderboard": cached_data}

    leaderboard = await database.get_top_leaderboard(limit=10)

    await redis_manager.cache_leaderboard(leaderboard, ttl=15)

    return {"source": "database", "leaderboard": leaderboard}
