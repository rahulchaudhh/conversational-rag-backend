import json

from redis import Redis

from app.core.config import settings


class RedisMemory:
    """Manage conversational memory using Redis Cloud."""

    def __init__(self) -> None:
        self.client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
        )

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Store one chat message for a session."""

        key = f"chat:{session_id}"

        message = {
            "role": role,
            "content": content,
        }

        self.client.rpush(
            key,
            json.dumps(message),
        )

    def get_messages(
        self,
        session_id: str,
    ) -> list[dict[str, str]]:
        """Retrieve all messages for a session."""

        key = f"chat:{session_id}"

        raw_messages = self.client.lrange(
            key,
            0,
            -1,
        )

        return [
            json.loads(message)
            for message in raw_messages
        ]

    def clear_session(
        self,
        session_id: str,
    ) -> None:
        """Delete conversation history for a session."""

        self.client.delete(
            f"chat:{session_id}"
        )