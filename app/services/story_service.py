from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import NotFoundError
from app.core.pagination import decode_keyset_cursor, encode_keyset_cursor
from app.db.models.story import Story
from app.repositories.story_repository import StoryRepository


class StoryService:
    def __init__(self, stories: StoryRepository) -> None:
        self.stories = stories
        self._settings = get_settings()

    async def get_story(self, story_id: UUID) -> Story:
        story = await self.stories.get_with_articles(story_id)
        if story is None:
            raise NotFoundError("Story not found.")
        return story

    async def list_stories(
        self, *, limit: int, cursor: str | None = None
    ) -> tuple[list[Story], str | None]:
        limit = max(1, min(limit, self._settings.feed_max_limit))
        decoded = decode_keyset_cursor(cursor) if cursor else None
        rows = await self.stories.list_page(limit=limit, cursor=decoded)

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            next_cursor = encode_keyset_cursor(rows[-1].created_at, rows[-1].id)
        return rows, next_cursor

    @staticmethod
    def sources_for(story: Story) -> list[str]:
        return sorted({a.source for a in story.articles})
