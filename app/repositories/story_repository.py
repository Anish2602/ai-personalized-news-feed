from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
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
            select(Story)
            .where(Story.id == story_id)
            .options(selectinload(Story.articles))
        )
        return result.scalar_one_or_none()

    async def article_count(self, story_id: UUID) -> int:
        result = await self.session.execute(
            select(Article.id).where(Article.story_id == story_id)
        )
        return len(result.all())

    async def update_summary(
        self, story_id: UUID, *, summary: str, canonical_title: str | None = None
    ) -> None:
        story = await self.session.get(Story, story_id)
        if story is not None:
            story.summary = summary
            if canonical_title:
                story.canonical_title = canonical_title[:500]
