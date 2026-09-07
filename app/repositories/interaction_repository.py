from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select

from app.db.models.article import Article
from app.db.models.interaction import Interaction, InteractionType
from app.repositories.base import BaseRepository


class InteractionRepository(BaseRepository):
    async def create(
        self, *, user_id: UUID, article_id: UUID, interaction_type: InteractionType
    ) -> Interaction:
        interaction = Interaction(
            user_id=user_id, article_id=article_id, interaction_type=interaction_type
        )
        self.session.add(interaction)
        await self.session.flush()
        return interaction

    async def list_by_user(self, user_id: UUID, *, limit: int = 200) -> list[Interaction]:
        result = await self.session.execute(
            select(Interaction)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def recent_for_profile(
        self, user_id: UUID, *, limit: int
    ) -> list[tuple[UUID, InteractionType, datetime]]:
        result = await self.session.execute(
            select(Interaction.article_id, Interaction.interaction_type, Interaction.created_at)
            .where(Interaction.user_id == user_id)
            .order_by(Interaction.created_at.desc())
            .limit(limit)
        )
        return [(r.article_id, r.interaction_type, r.created_at) for r in result.all()]

    async def story_engagement(
        self, story_ids: list[UUID]
    ) -> dict[UUID, dict[InteractionType, int]]:
        """Interaction-type counts per story (single grouped query — no N+1)."""
        if not story_ids:
            return {}
        result = await self.session.execute(
            select(
                Article.story_id,
                Interaction.interaction_type,
                func.count().label("n"),
            )
            .join(Interaction, Interaction.article_id == Article.id)
            .where(Article.story_id.in_(story_ids))
            .group_by(Article.story_id, Interaction.interaction_type)
        )
        out: dict[UUID, dict[InteractionType, int]] = {}
        for story_id, itype, n in result.all():
            out.setdefault(story_id, {})[itype] = n
        return out

    async def user_story_signals(
        self, user_id: UUID, story_ids: list[UUID]
    ) -> dict[UUID, set[InteractionType]]:
        """Which interaction types this user has on each candidate story."""
        if not story_ids:
            return {}
        result = await self.session.execute(
            select(Article.story_id, Interaction.interaction_type)
            .join(Interaction, Interaction.article_id == Article.id)
            .where(
                Article.story_id.in_(story_ids),
                Interaction.user_id == user_id,
            )
            .distinct()
        )
        out: dict[UUID, set[InteractionType]] = {}
        for story_id, itype in result.all():
            out.setdefault(story_id, set()).add(itype)
        return out
