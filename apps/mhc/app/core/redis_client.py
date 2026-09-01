import logging
import os
from typing import Optional

import redis
from redis.exceptions import RedisError

try:
    import fakeredis
except ModuleNotFoundError:  # pragma: no cover
    fakeredis = None  # type: ignore

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_redis_url() -> str:
    """Redis URL from settings or env (fallback for Docker/compose edge cases)."""
    url = getattr(settings, "REDIS_URL", None) or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return url


def _should_use_fallback() -> bool:
    """Return True when we are in a non-production environment."""
    return settings.DEBUG or settings.ENVIRONMENT.lower() in {"development", "local", "test"}


def _create_redis_client() -> redis.Redis:
    """Create a Redis client and fall back to fakeredis when allowed."""
    redis_url = _get_redis_url()
    client = redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
    )

    try:
        client.ping()
        logger.info("Connected to Redis at %s", redis_url)
        return client
    except RedisError as exc:
        if _should_use_fallback() and fakeredis is not None:
            logger.warning(
                "Redis unavailable (%s). Falling back to in-memory fakeredis instance.",
                exc,
            )
            return fakeredis.FakeStrictRedis(decode_responses=True)

        logger.error("Redis connection failed and no fallback is available: %s", exc)
        raise


redis_client: Optional[redis.Redis] = None

try:
    redis_client = _create_redis_client()
except RedisError as exc:
    # Permettre de continuer sans Redis même en production
    # L'application fonctionnera en mode dégradé (sans refresh tokens, cache, etc.)
    logger.error(
        "⚠️ Redis non disponible (%s). L'application démarre en mode dégradé. "
        "Certaines fonctionnalités (refresh tokens, cache, sessions) ne seront pas disponibles. "
        "Veuillez démarrer Redis pour une expérience complète.",
        exc
    )
    redis_client = None


def get_redis() -> Optional[redis.Redis]:
    """Dependency for getting Redis client."""
    if redis_client is None:
        # Retourner None au lieu de lever une exception
        # L'application peut fonctionner en mode dégradé
        logger.debug("Redis non disponible - certaines fonctionnalités seront désactivées")
        return None
    return redis_client


