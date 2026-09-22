import json
import logging
from typing import Optional
from redis import ConnectionPool, Redis
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Shared global connection pool
_redis_pool: Optional[ConnectionPool] = None


def get_redis_pool() -> Optional[ConnectionPool]:
    global _redis_pool
    if _redis_pool is None:
        if not settings.redis_url:
            logger.warning("REDIS_URL is not configured.")
            return None
        try:
            retry = Retry(ExponentialBackoff(), 3)
            _redis_pool = ConnectionPool.from_url(
                settings.redis_url,
                decode_responses=True,
                retry=retry,
                retry_on_error=[ConnectionError, TimeoutError],
                health_check_interval=30,
                socket_keepalive=True,
                socket_timeout=15,
                max_connections=20,
            )
        except Exception as exc:
            logger.error(f"Failed to create Redis ConnectionPool: {exc}")
            return None
    return _redis_pool


class RedisMemory:
    """Manage conversational memory using Redis with connection pooling, auto-reconnect, and error tolerance."""

    def __init__(self) -> None:
        self._client: Optional[Redis] = None

    @property
    def client(self) -> Optional[Redis]:
        """Lazy-loaded Redis client using shared connection pool."""
        if self._client is None:
            pool = get_redis_pool()
            if pool is not None:
                self._client = Redis(connection_pool=pool)
        return self._client

    def is_available(self) -> bool:
        """Check if Redis connection is working."""
        cli = self.client
        if cli is None:
            return False
        try:
            return bool(cli.ping())
        except Exception:
            return False

    def close(self) -> None:
        """Close client and disconnect connection pool."""
        global _redis_pool
        if self._client is not None:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"Error closing Redis client: {e}")
            self._client = None
        if _redis_pool is not None:
            try:
                _redis_pool.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting Redis connection pool: {e}")
            _redis_pool = None


    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> None:
        """Store one chat message for a session with retry."""
        cli = self.client
        if cli is None:
            logger.warning(f"Cannot add message to Redis for session {session_id}: Redis not available.")
            return

        key = f"chat:{session_id}"
        message = {
            "role": role,
            "content": content,
        }

        try:
            cli.rpush(key, json.dumps(message))
        except (ConnectionError, TimeoutError):
            logger.warning("Redis connection dropped, retrying push...")
            try:
                cli.rpush(key, json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to retry add message to Redis: {e}")
        except Exception as e:
            logger.error(f"Failed to add message to Redis: {e}")

    def get_messages(
        self,
        session_id: str,
    ) -> list[dict[str, str]]:
        """Retrieve all messages for a session with retry."""
        cli = self.client
        if cli is None:
            logger.warning(f"Cannot get messages from Redis for session {session_id}: Redis not available.")
            return []

        key = f"chat:{session_id}"

        try:
            raw_messages = cli.lrange(key, 0, -1)
        except (ConnectionError, TimeoutError):
            logger.warning("Redis connection dropped during get_messages, retrying...")
            try:
                raw_messages = cli.lrange(key, 0, -1)
            except Exception as e:
                logger.error(f"Failed to retry get messages from Redis: {e}")
                return []
        except Exception as e:
            logger.error(f"Failed to get messages from Redis: {e}")
            return []

        messages = []
        for message in raw_messages:
            try:
                messages.append(json.loads(message))
            except Exception:
                continue
        return messages

    def clear_session(
        self,
        session_id: str,
    ) -> None:
        """Delete conversation history for a session."""
        cli = self.client
        if cli is None:
            return

        try:
            cli.delete(f"chat:{session_id}")
        except (ConnectionError, TimeoutError):
            try:
                cli.delete(f"chat:{session_id}")
            except Exception as e:
                logger.error(f"Failed to clear Redis session: {e}")
        except Exception as e:
            logger.error(f"Failed to clear Redis session: {e}")

    def get_all_sessions(self) -> list[dict[str, any]]:
        """Retrieve all active chat sessions from Redis."""
        cli = self.client
        if cli is None:
            return []

        try:
            keys = cli.keys("chat:*")
        except Exception as e:
            logger.error(f"Failed to retrieve chat session keys: {e}")
            return []

        sessions = []
        for key in keys:
            session_id = key[5:] if key.startswith("chat:") else key
            try:
                raw_messages = cli.lrange(key, 0, -1)
            except Exception:
                continue

            if not raw_messages:
                continue

            try:
                parsed = [json.loads(m) for m in raw_messages]
            except Exception:
                continue

            # Derive title from the first user message, or default to session_id
            first_user_msg = next((m.get("content", "") for m in parsed if m.get("role") == "user"), None)
            if first_user_msg:
                clean_title = first_user_msg.strip().replace("\n", " ")
                title = clean_title[:40] + ("..." if len(clean_title) > 40 else "")
            else:
                title = session_id

            last_msg = parsed[-1].get("content", "") if parsed else ""
            clean_last = last_msg.strip().replace("\n", " ")
            snippet = clean_last[:60] + ("..." if len(clean_last) > 60 else "")

            sessions.append({
                "session_id": session_id,
                "title": title,
                "message_count": len(parsed),
                "last_message": snippet,
            })

        # Sort by message count or title
        sessions.sort(key=lambda s: s["message_count"], reverse=True)
        return sessions