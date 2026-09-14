from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.user import Interest, User, UserInterest
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    async def create(self, *, email: str, name: str) -> User:
        user = User(email=email, name=name)
        self.session.add(user)
        await self.session.flush()
        return user

    async def get(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_or_create_interest(self, name: str) -> Interest:
        result = await self.session.execute(select(Interest).where(Interest.name == name))
        interest = result.scalar_one_or_none()
        if interest is None:
            interest = Interest(name=name)
            self.session.add(interest)
            await self.session.flush()
        return interest

    async def upsert_user_interest(
        self, *, user_id: UUID, interest_id: UUID, weight: float
    ) -> UserInterest:
        link = await self.session.get(UserInterest, (user_id, interest_id))
        if link is None:
            link = UserInterest(user_id=user_id, interest_id=interest_id, weight=weight)
            self.session.add(link)
            await self.session.flush()
        else:
            link.weight = weight
        return link

    async def list_interests(self, user_id: UUID) -> list[UserInterest]:
        result = await self.session.execute(
            select(UserInterest)
            .where(UserInterest.user_id == user_id)
            .options(selectinload(UserInterest.interest))
            .order_by(UserInterest.created_at)
        )
        return list(result.scalars().all())

    async def delete_user_interest(self, *, user_id: UUID, name: str) -> bool:
        result = await self.session.execute(
            select(UserInterest)
            .join(Interest)
            .where(UserInterest.user_id == user_id, Interest.name == name)
        )
        link = result.scalar_one_or_none()
        if link is None:
            return False
        await self.session.delete(link)
        await self.session.flush()
        return True
