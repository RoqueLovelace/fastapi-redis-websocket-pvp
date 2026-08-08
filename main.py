import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

import redis_client
from db import close_db_pool, init_db_pool
from game.router import router as game_router
from leaderboard.router import router as leaderboard_router
from users.router import router as users_router
from ws.manager import redis_pubsub_listener
from ws.router import router as ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
  await init_db_pool()
  await redis_client.init_redis_pool()

  listener_task = asyncio.create_task(redis_pubsub_listener())
  print("[SERVER] FastAPI is ready to accept connections!")

  yield

  listener_task.cancel()
  await redis_client.close_redis_pool()
  await close_db_pool()
  print("[SERVER] FastAPI shut down safely.")


app = FastAPI(lifespan=lifespan, title="Coin Flip PvP API")

app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(users_router)
app.include_router(game_router)
app.include_router(leaderboard_router)
app.include_router(ws_router)


@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
  html_path = os.path.join(os.path.dirname(__file__), "index.html")
  if os.path.exists(html_path):
    with open(html_path, "r", encoding="utf-8") as f:
      return f.read()
  return "<h1>index.html not found</h1>"
