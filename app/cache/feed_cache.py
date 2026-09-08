"""Per-user feed snapshot cache.

One Redis key per user (``feed:user:{user_id}``) holds the *whole* ranked story
list for the current snapshot. Pages are sliced from it in the application by the
opaque offset cursor. A single snapshot means every page of a pagination walk is
consistent, and one ``DEL`` invalidates the entire feed.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import redis.asyncio as aioredis
from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.ranking.scorer import RankFeatures

logger = get_logger(__name__)


class CachedFeedItem(BaseModel):
    story_id: UUID
    score: float
    features: RankFeatures
    contributions: dict[str, float]


class CachedFeed(BaseModel):
    generated_at: datetime
    cold_start: bool
    items: list[CachedFeedItem]


class FeedCache:
    def __init__(self, redis: aioredis.Redis, *, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    @staticmethod
    def key(user_id: UUID) -> str:
        return f"feed:user:{user_id}"

    async def get(self, user_id: UUID) -> CachedFeed | None:
        try:
            raw = await self._redis.get(self.key(user_id))
        except Exception as exc:  # noqa: BLE001 - a cache outage must not break the feed
            logger.warning("feed_cache_get_failed", error=str(exc))
            return None
        if raw is None:
            return None
        try:
            return CachedFeed.model_validate_json(raw)
        except ValidationError:
            logger.warning("feed_cache_corrupt", user_id=str(user_id))
            return None

    async def set(self, user_id: UUID, feed: CachedFeed) -> None:
        try:
            await self._redis.set(self.key(user_id), feed.model_dump_json(), ex=self._ttl)
        except Exception as exc:  # noqa: BLE001
            logger.warning("feed_cache_set_failed", error=str(exc))

    async def invalidate(self, user_id: UUID) -> None:
        try:
            await self._redis.delete(self.key(user_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("feed_cache_invalidate_failed", error=str(exc))
