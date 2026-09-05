from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.db.models.interaction import Interaction, InteractionType
from app.repositories.article_repository import ArticleRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.user_repository import UserRepository
from app.schemas.interaction import InteractionCreate

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
    ) -> None:
        self.interactions = interactions
        self.users = users
        self.articles = articles

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
        # Phase 6/7: enqueue rebuild_user_profile(user_id) and invalidate the
        # user's feed cache on high-signal interactions.
        return interaction

    async def list_for_user(self, user_id: UUID, *, limit: int = 200) -> list[Interaction]:
        return await self.interactions.list_by_user(user_id, limit=limit)
