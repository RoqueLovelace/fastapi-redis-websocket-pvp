from sqlalchemy import select

from .models import ChatMessage, Match, User
from .session import get_session_maker


async def get_or_create_user(username: str) -> dict:
    session_maker = get_session_maker()

    async with session_maker() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user:
            return user.to_public_dict()

        user = User(username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user.to_public_dict()


def calculate_streak_multiplier(streak: int) -> int:
    """Returns a positive streak multiplier (e.g., 1x, 2x, 3x)."""
    abs_streak = abs(streak)
    return 1 if abs_streak == 0 else abs_streak


async def record_match(winner_id: int, loser_id: int, stake: int, outcome: bool) -> dict:
    session_maker = get_session_maker()

    async with session_maker() as session:
        async with session.begin():
            locked_ids = sorted([winner_id, loser_id])
            result = await session.execute(
                select(User).where(User.id.in_(locked_ids)).with_for_update().order_by(User.id)
            )
            users_by_id = {u.id: u for u in result.scalars().all()}

            winner = users_by_id.get(winner_id)
            if not winner:
                raise RuntimeError("[ERROR] Winner not found")
            loser = users_by_id.get(loser_id)
            if not loser:
                raise RuntimeError("[ERROR] Loser not found")

            w_streak = winner.streak
            w_score = winner.score
            w_max_streak = winner.max_streak
            l_streak = loser.streak
            l_score = loser.score

            new_w_streak = w_streak + 1 if w_streak > 0 else 1
            new_w_max_streak = max(new_w_streak, w_max_streak)

            w_multiplier = calculate_streak_multiplier(w_streak if w_streak > 0 else 1)
            w_adjustment = stake * w_multiplier
            new_w_score = w_score + w_adjustment

            new_l_streak = l_streak - 1 if l_streak < 0 else -1

            l_multiplier = calculate_streak_multiplier(l_streak if l_streak < 0 else -1)
            l_adjustment = -(stake * l_multiplier)
            new_l_score = max(0, l_score + l_adjustment)  # Floor score at 0

            winner.score = new_w_score
            winner.streak = new_w_streak
            winner.max_streak = new_w_max_streak
            winner.max_score = max(winner.max_score, new_w_score)

            loser.score = new_l_score
            loser.streak = new_l_streak
            loser.max_score = max(loser.max_score, new_l_score)

            match = Match(winner_id=winner_id, loser_id=loser_id, outcome=outcome)
            session.add(match)
            await session.flush()

            w_dict = winner.to_public_dict()
            w_dict["score_adjustment"] = w_adjustment
            l_dict = loser.to_public_dict()
            l_dict["score_adjustment"] = l_adjustment

            return {
                "match_id": match.id,
                "winner": w_dict,
                "loser": l_dict,
                "recorded_at": match.created_at,
            }


async def save_chat_message(sender_id: int, message: str, room_id: str = "global", receiver_id: int | None = None) -> str:
    session_maker = get_session_maker()

    async with session_maker() as session:
        chat_message = ChatMessage(
            sender_id=sender_id,
            message_text=message,
            receiver_id=receiver_id,
            room_id=room_id,
        )
        session.add(chat_message)
        await session.commit()
        await session.refresh(chat_message)

        if not chat_message.public_id:
            raise RuntimeError("[ERROR] Insertion failed")

        return str(chat_message.public_id)


async def mark_messages_as_read(room_id: str, receiver_id: int) -> int:
    session_maker = get_session_maker()

    async with session_maker() as session:
        result = await session.execute(
            select(ChatMessage).where(
                ChatMessage.room_id == room_id,
                ChatMessage.receiver_id == receiver_id,
                ChatMessage.is_read.is_(False),
            )
        )
        messages = result.scalars().all()
        for msg in messages:
            msg.is_read = True

        await session.commit()
        return len(messages)


async def get_top_leaderboard(limit: int = 10) -> list[dict]:
    session_maker = get_session_maker()

    async with session_maker() as session:
        result = await session.execute(
            select(User).order_by(User.score.desc(), User.max_streak.desc()).limit(limit)
        )
        users = result.scalars().all()

        leaderboard = []
        for user in users:
            leaderboard.append(
                {
                    "id": user.id,
                    "public_id": str(user.public_id),
                    "username": user.username,
                    "score": user.score,
                    "streak": user.streak,
                    "max_streak": user.max_streak,
                }
            )
        return leaderboard
