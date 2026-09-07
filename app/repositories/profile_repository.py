from __future__ import annotations

from uuid import UUID

from app.db.models.profile import UserProfile
from app.repositories.base import BaseRepository


class ProfileRepository(BaseRepository):
    async def get(self, user_id: UUID) -> UserProfile | None:
        return await self.session.get(UserProfile, user_id)

    async def upsert(
        self,
        user_id: UUID,
        *,
        embedding: list[float] | None,
        interaction_count: int,
        embedding_model: str | None,
    ) -> UserProfile:
        profile = await self.session.get(UserProfile, user_id)
        if profile is None:
            profile = UserProfile(user_id=user_id)
            self.session.add(profile)
        profile.embedding = embedding
        profile.interaction_count = interaction_count
        profile.embedding_model = embedding_model
        await self.session.flush()
        return profile
