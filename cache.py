# cache.py
import os
import json
import logging
from typing import Any, Optional, TYPE_CHECKING

logger = logging.getLogger("uvicorn.error")

# For type checking only (prevents Pylance warnings)
if TYPE_CHECKING:
    import redis.asyncio as redis_asyncio

# Runtime import (safe if redis isn't installed)
try:
    import redis.asyncio as redis_asyncio_runtime
except Exception:
    redis_asyncio_runtime = None  # type: ignore

_redis_client: Optional["redis_asyncio.Redis"] = None


def _build_redis_url() -> Optional[str]:
    """
    Builds a Redis connection URL from environment variables.

    Priority:
      1) REDIS_URL (preferred)
      2) REDIS_HOST / REDIS_PORT / REDIS_USERNAME / REDIS_PASSWORD

    Notes:
      - REDIS_HOST must NOT include the port (we strip it if it does).
      - Redis Cloud typically requires username + password (often username is "default").
    """
    redis_url = os.getenv("REDIS_URL")
    if redis_url:
        return redis_url.strip()

    host = os.getenv("REDIS_HOST")
    port = os.getenv("REDIS_PORT")
    username = os.getenv("REDIS_USERNAME")
    password = os.getenv("REDIS_PASSWORD")

    if not host or not port:
        return None

    # If someone accidentally put host:port in REDIS_HOST, strip it.
    host = host.strip()
    if ":" in host:
        host = host.split(":", 1)[0]

    port = str(port).strip()

    # Best practice for Redis Cloud: include username + password if present
    if username and password:
        return f"redis://{username}:{password}@{host}:{port}"

    # Fallback patterns (some providers accept empty username)
    if password and not username:
        return f"redis://:{password}@{host}:{port}"

    return f"redis://{host}:{port}"


async def get_redis_client() -> Optional["redis_asyncio.Redis"]:
    """
    Returns a singleton Redis client, or None if Redis is not configured/available.

    This is async because we "ping" to verify connectivity + credentials.
    """
    global _redis_client

    if _redis_client is not None:
        return _redis_client

    if redis_asyncio_runtime is None:
        logger.warning("Redis library not installed; caching disabled.")
        return None

    url = _build_redis_url()
    if not url:
        logger.warning("Redis not configured (no REDIS_URL or REDIS_HOST/PORT); caching disabled.")
        return None

    try:
        client = redis_asyncio_runtime.from_url(url, encoding="utf-8", decode_responses=True)

        # Verify the connection & auth now (so errors show up early and clearly)
        await client.ping()

        _redis_client = client
        logger.info("Redis cache connected successfully.")
        return _redis_client

    except Exception as e:
        logger.exception(f"Redis connection/auth failed; caching disabled. Error: {e!r}")
        _redis_client = None
        return None


async def get_cached_data(key: str) -> Optional[Any]:
    """
    Get JSON-serializable data from Redis. Returns None if not found or cache unavailable.
    """
    client = await get_redis_client()
    if client is None:
        return None

    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.exception(f"Redis read failed for key={key!r}: {e!r}")
        return None


async def set_cache_data(key: str, value: Any, expiration: int = 3600) -> bool:
    """
    Set JSON-serializable data in Redis. Returns True if stored, False if cache unavailable/fails.
    """
    client = await get_redis_client()
    if client is None:
        return False

    try:
        raw = json.dumps(value)
        await client.set(key, raw, ex=expiration)
        return True
    except Exception as e:
        logger.exception(f"Redis write failed for key={key!r}: {e!r}")
        return False
