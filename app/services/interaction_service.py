from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from app.cache.feed_cache import FeedCache
from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models.interaction import Interaction, InteractionType
from app.repositories.article_repository import ArticleRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.interaction import InteractionCreate

QueueProfileRebuild = Callable[[UUID], None]

logger = get_logger(__name__)


def interaction_weight(interaction_type: InteractionType) -> float:
    """Signed weight for an interaction, sourced entirely from configuration."""
    return get_settings().interaction_weights[interaction_type.value]


class InteractionService:
    def __init__(
        self,
        interactions: InteractionRepository,
        users: UserRepository,
        articles: ArticleRepository,
        queue_profile_rebuild: QueueProfileRebuild | None = None,
        feed_cache: FeedCache | None = None,
    ) -> None:
        self.interactions = interactions
        self.users = users
        self.articles = articles
        self._queue_profile_rebuild = queue_profile_rebuild or (lambda _uid: None)
        self._feed_cache = feed_cache
        self._settings = get_settings()

    async def record(self, payload: InteractionCreate) -> Interaction:
        if await self.users.get(payload.user_id) is None:
            raise NotFoundError("User not found.")
        if await self.articles.get(payload.article_id) is None:
            raise NotFoundError("Article not found.")

        interaction = await self.interactions.create(
            user_id=payload.user_id,
            article_id=payload.article_id,
            interaction_type=payload.interaction_type,
        )
        logger.info(
            "interaction_recorded",
            user_id=str(payload.user_id),
            article_id=str(payload.article_id),
            interaction_type=payload.interaction_type.value,
            weight=interaction_weight(payload.interaction_type),
        )
        # Recompute the user's interest vector in the background.
        self._queue_profile_rebuild(payload.user_id)
        # Drop the cached feed so the next request reflects this signal.
        if (
            self._feed_cache is not None
            and payload.interaction_type.value in self._settings.feed_cache_invalidate_types
        ):
            await self._feed_cache.invalidate(payload.user_id)
        return interaction

    async def list_for_user(self, user_id: UUID, *, limit: int = 200) -> list[Interaction]:
        return await self.interactions.list_by_user(user_id, limit=limit)
