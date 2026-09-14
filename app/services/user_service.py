from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.cache.feed_cache import FeedCache
from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.db.models.user import User, UserInterest
from app.repositories.user_repository import UserRepository
from app.schemas.user import InterestAssignItem, UserCreate

logger = get_logger(__name__)


class UserService:
    def __init__(self, users: UserRepository, feed_cache: FeedCache | None = None) -> None:
        self.users = users
        self._feed_cache = feed_cache

    async def create_user(self, payload: UserCreate) -> User:
        if await self.users.get_by_email(payload.email):
            raise ConflictError("A user with this email already exists.")
        try:
            user = await self.users.create(email=payload.email, name=payload.name)
        except IntegrityError as exc:  # race: unique violation between check and insert
            raise ConflictError("A user with this email already exists.") from exc
        logger.info("user_created", user_id=str(user.id))
        return user

    async def get_user(self, user_id: UUID) -> User:
        user = await self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found.")
        return user

    async def assign_interests(
        self, user_id: UUID, items: list[InterestAssignItem]
    ) -> list[UserInterest]:
        await self.get_user(user_id)
        for item in items:
            interest = await self.users.get_or_create_interest(item.name)
            await self.users.upsert_user_interest(
                user_id=user_id, interest_id=interest.id, weight=item.weight
            )
        logger.info("user_interests_assigned", user_id=str(user_id), count=len(items))
        if self._feed_cache is not None:
            await self._feed_cache.invalidate(user_id)
        return await self.users.list_interests(user_id)

    async def list_interests(self, user_id: UUID) -> list[UserInterest]:
        await self.get_user(user_id)
        return await self.users.list_interests(user_id)

    async def remove_interest(self, user_id: UUID, name: str) -> None:
        await self.get_user(user_id)
        deleted = await self.users.delete_user_interest(user_id=user_id, name=name)
        if not deleted:
            raise NotFoundError("Interest not found for this user.")
        logger.info("user_interest_removed", user_id=str(user_id), name=name)
        if self._feed_cache is not None:
            await self._feed_cache.invalidate(user_id)
