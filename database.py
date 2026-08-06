from dotenv import load_dotenv
import os
import asyncpg
from typing import cast

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

pool: asyncpg.Pool | None = None

USER_PUBLIC_FIELDS = "id, public_id, username, streak, max_streak, score"

async def init_db_pool():
    global pool
    print("[INFO] Initializing Database Pool...")
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    async with pool.acquire() as raw_conn:
        conn = cast(asyncpg.Connection, raw_conn)
        await conn.execute("""
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            CREATE TABLE IF NOT EXISTS users (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                public_id UUID DEFAULT gen_random_uuid() UNIQUE,
                username VARCHAR(20) NOT NULL,
                streak INT NOT NULL DEFAULT 0,
                max_streak INT NOT NULL DEFAULT 0,
                max_score INT NOT NULL DEFAULT 500,
                score INT NOT NULL DEFAULT 500,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP 
            );

            CREATE TABLE IF NOT EXISTS chat_messages (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                public_id UUID DEFAULT gen_random_uuid() UNIQUE,
                sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                room_id VARCHAR(20) NOT NULL,
                message_text TEXT NOT NULL,
                is_read BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP 
            );
            CREATE INDEX IF NOT EXISTS idx_messages_sender ON chat_messages(sender_id);
            CREATE INDEX IF NOT EXISTS idx_messages_receiver ON chat_messages(receiver_id);

            CREATE TABLE IF NOT EXISTS matches (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                public_id UUID DEFAULT gen_random_uuid() UNIQUE,
                winner_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                loser_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                outcome BOOLEAN NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP 
            );

            CREATE TABLE IF NOT EXISTS leaderboard_snapshots (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                final_rank INT NOT NULL,
                final_score INT NOT NULL,
                season_name VARCHAR(30) NOT NULL,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP 
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_season ON leaderboard_snapshots(season_name);
        """)
    print("[INFO] Database pool initialized.")


async def close_db_pool() -> None:
    global pool
    if pool:
        await pool.close()


async def get_or_create_user(username: str) -> dict:
    global pool
    if not pool:
        raise RuntimeError("[ERROR] There are no connections to the Database")

    async with pool.acquire() as raw_conn:
        conn = cast(asyncpg.Connection, raw_conn)
        get_query = f"""
            SELECT {USER_PUBLIC_FIELDS} FROM users
            WHERE username = $1
        """

        row = await conn.fetchrow(get_query, username)
        if row:
            return dict(row)

        insert_query = f""" INSERT INTO users (username) VALUES($1) RETURNING {USER_PUBLIC_FIELDS} """
        result = await conn.fetchrow(insert_query, username)
        new_row = cast(asyncpg.Record, result)
        return dict(new_row)


def calculate_streak_multiplier(streak: int) -> int:
    """Returns a positive streak multiplier (e.g., 1x, 2x, 3x)."""
    abs_streak = abs(streak)
    return 1 if abs_streak == 0 else abs_streak


async def record_match(winner_id: int, loser_id: int, stake: int, outcome: bool) -> dict:
    global pool
    if not pool:
        raise RuntimeError("[ERROR] There are no connections to the Database")

    async with pool.acquire() as raw_conn:
        conn = cast(asyncpg.Connection, raw_conn)
        async with conn.transaction():
            get_query = "SELECT * FROM users WHERE id = $1"

            winner = await conn.fetchrow(get_query, winner_id)
            if not winner:
                raise RuntimeError("[ERROR] Winner not found")
            loser = await conn.fetchrow(get_query, loser_id)
            if not loser:
                raise RuntimeError("[ERROR] Loser not found")

            w_streak = winner["streak"]
            w_score = winner["score"]
            w_max_streak = winner["max_streak"]
            l_streak = loser["streak"]
            l_score = loser["score"]

            new_w_streak = w_streak + 1 if w_streak > 0 else 1
            new_w_max_streak = max(new_w_streak, w_max_streak)
            
            w_multiplier = calculate_streak_multiplier(w_streak if w_streak > 0 else 1)
            w_adjustment = stake * w_multiplier
            new_w_score = w_score + w_adjustment

            new_l_streak = l_streak - 1 if l_streak < 0 else -1
            
            l_multiplier = calculate_streak_multiplier(l_streak if l_streak < 0 else -1)
            l_adjustment = -(stake * l_multiplier)
            new_l_score = max(0, l_score + l_adjustment) # Floor score at 0

            update_query = f""" 
                UPDATE users
                SET score = $1, streak = $2, max_streak = $3, max_score = GREATEST(max_score, $1)
                WHERE id = $4
                RETURNING {USER_PUBLIC_FIELDS}
            """

            updated_winner = await conn.fetchrow(update_query, new_w_score, new_w_streak, new_w_max_streak, winner_id)
            updated_loser = await conn.fetchrow(update_query, new_l_score, new_l_streak, loser["max_streak"], loser_id)

            match_query = """
                INSERT INTO matches (winner_id, loser_id, outcome) VALUES ($1, $2, $3)
                RETURNING id, created_at
            """

            match_record = await conn.fetchrow(match_query, winner_id, loser_id, outcome)
            if not match_record:
                raise RuntimeError("[ERROR] Could not retrieve match info")

            w_dict = dict(cast(asyncpg.Record, updated_winner))
            w_dict["score_adjustment"] = w_adjustment
            l_dict = dict(cast(asyncpg.Record, updated_loser))
            l_dict["score_adjustment"] = l_adjustment

            return {
                "match_id": match_record["id"],
                "winner": w_dict,
                "loser": l_dict,
                "recorded_at": match_record["created_at"]
            }


async def save_chat_message(sender_id: int, message: str, room_id: str = "global", receiver_id: int | None = None) -> str:
    global pool
    if not pool:
        raise RuntimeError("[ERROR] There are no connections to the Database")

    async with pool.acquire() as raw_conn:
        conn = cast(asyncpg.Connection, raw_conn) 
        insert_query = """
            INSERT INTO chat_messages (sender_id, message_text, receiver_id, room_id)
            VALUES ($1, $2, $3, $4)
            RETURNING public_id
        """
        message_pid = await conn.fetchval(insert_query, sender_id, message, receiver_id, room_id)
        if not message_pid:
            raise RuntimeError("[ERROR] Insertion failed")

        return str(message_pid)


async def mark_messages_as_read(room_id: str, receiver_id: int) -> int:
    global pool
    if not pool:
        raise RuntimeError("[ERROR] There are no connections to the Database")

    async with pool.acquire() as raw_conn:
        conn = cast(asyncpg.Connection, raw_conn) 
        update_query = """
            UPDATE chat_messages
            SET is_read = TRUE
            WHERE room_id = $1 AND receiver_id = $2 AND is_read = FALSE
        """
        status = await conn.execute(update_query, room_id, receiver_id)
        return int(status.split()[-1])


async def get_top_leaderboard(limit: int = 10) -> list[dict]:
    global pool
    if not pool:
        raise RuntimeError("[ERROR] There are no connections to the Database")

    async with pool.acquire() as raw_conn:
        conn = cast(asyncpg.Connection, raw_conn)
        query = f"""
            SELECT id, public_id, username, score, streak, max_streak 
            FROM users 
            ORDER BY score DESC, max_streak DESC 
            LIMIT $1
        """
        rows = await conn.fetch(query, limit)
        leaderboard = []
        for row in rows:
            user_dict = dict(row)
            user_dict["public_id"] = str(user_dict["public_id"])
            leaderboard.append(user_dict)
        return leaderboard
