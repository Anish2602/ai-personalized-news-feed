from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

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
