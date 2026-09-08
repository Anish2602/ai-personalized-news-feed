from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import selectinload

from app.db.models.article import Article
from app.db.models.story import Story
from app.repositories.base import BaseRepository


class StoryRepository(BaseRepository):
    async def create(self, *, canonical_title: str, summary: str | None = None) -> Story:
        story = Story(canonical_title=canonical_title[:500], summary=summary)
        self.session.add(story)
        await self.session.flush()
        return story

    async def get(self, story_id: UUID) -> Story | None:
        return await self.session.get(Story, story_id)

    async def get_with_articles(self, story_id: UUID) -> Story | None:
        result = await self.session.execute(
            select(Story).where(Story.id == story_id).options(selectinload(Story.articles))
        )
        return result.scalar_one_or_none()

    async def get_many_with_articles(self, story_ids: list[UUID]) -> list[Story]:
        if not story_ids:
            return []
        result = await self.session.execute(
            select(Story).where(Story.id.in_(story_ids)).options(selectinload(Story.articles))
        )
        return list(result.scalars().all())

    async def recent_with_articles(self, *, limit: int) -> list[Story]:
        result = await self.session.execute(
            select(Story)
            .options(selectinload(Story.articles))
            .order_by(Story.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_page(
        self, *, limit: int, cursor: tuple[datetime, str] | None = None
    ) -> list[Story]:
        stmt = select(Story).options(selectinload(Story.articles))
        if cursor is not None:
            cur_ts, cur_id = cursor
            stmt = stmt.where(
                or_(
                    Story.created_at < cur_ts,
                    and_(Story.created_at == cur_ts, Story.id < cur_id),
                )
            )
        stmt = stmt.order_by(Story.created_at.desc(), Story.id.desc()).limit(limit + 1)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def article_count(self, story_id: UUID) -> int:
        result = await self.session.execute(select(Article.id).where(Article.story_id == story_id))
        return len(result.all())

    async def set_topics(self, story_id: UUID, topics: list[str]) -> None:
        story = await self.session.get(Story, story_id)
        if story is not None:
            story.topics = list(topics)

    async def set_enrichment(
        self,
        story_id: UUID,
        *,
        summary: str,
        key_points: list[str],
        topics: list[str],
        canonical_title: str | None = None,
    ) -> None:
        story = await self.session.get(Story, story_id)
        if story is None:
            return
        story.summary = summary
        story.key_points = list(key_points)
        story.topics = list(topics)
        if canonical_title:
            story.canonical_title = canonical_title[:500]
