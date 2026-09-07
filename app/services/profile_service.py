"""Rebuild a user's interest vector from their recent interactions."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.ai.embeddings import get_embedding_provider
from app.ai.profile_builder import aggregate_weights_by_article, weighted_profile
from app.core.config import get_settings
from app.core.logging import get_logger
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.vector.search import VectorStoreProtocol

logger = get_logger(__name__)


class ProfileResult(BaseModel):
    user_id: UUID
    has_vector: bool
    interaction_count: int
    articles_used: int


class ProfileService:
    def __init__(
        self,
        interactions: InteractionRepository,
        profiles: ProfileRepository,
        vectors: VectorStoreProtocol,
    ) -> None:
        self.interactions = interactions
        self.profiles = profiles
        self.vectors = vectors
        self._settings = get_settings()

    async def rebuild(self, user_id: UUID) -> ProfileResult:
        weights_cfg = self._settings.interaction_weights
        recent = await self.interactions.recent_for_profile(
            user_id, limit=self._settings.profile_max_interactions
        )
        per_article = aggregate_weights_by_article(
            (str(article_id), weights_cfg[itype.value]) for article_id, itype, _ in recent
        )

        vectors_by_id: dict[str, list[float]] = {}
        if per_article:
            vectors_by_id = await self.vectors.retrieve_vectors(list(per_article))

        items = [(vec, per_article[aid]) for aid, vec in vectors_by_id.items()]
        profile_vec = weighted_profile(items)

        await self.profiles.upsert(
            user_id,
            embedding=profile_vec,
            interaction_count=len(recent),
            embedding_model=get_embedding_provider().model_name if profile_vec else None,
        )
        logger.info(
            "user_profile_rebuilt",
            user_id=str(user_id),
            interactions=len(recent),
            articles_used=len(items),
            has_vector=profile_vec is not None,
        )
        return ProfileResult(
            user_id=user_id,
            has_vector=profile_vec is not None,
            interaction_count=len(recent),
            articles_used=len(items),
        )
