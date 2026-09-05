from __future__ import annotations

from uuid import UUID

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationError
from app.core.pagination import decode_keyset_cursor, encode_keyset_cursor
from app.db.models.article import Article, ArticleProcessingStatus
from app.repositories.article_repository import ArticleRepository


class ArticleService:
    def __init__(self, articles: ArticleRepository) -> None:
        self.articles = articles
        self._settings = get_settings()

    async def get_article(self, article_id: UUID) -> Article:
        article = await self.articles.get(article_id)
        if article is None:
            raise NotFoundError("Article not found.")
        return article

    async def list_articles(
        self,
        *,
        limit: int,
        source: str | None = None,
        status: str | None = None,
        cursor: str | None = None,
    ) -> tuple[list[Article], str | None]:
        limit = max(1, min(limit, self._settings.feed_max_limit))

        status_enum: ArticleProcessingStatus | None = None
        if status is not None:
            try:
                status_enum = ArticleProcessingStatus(status.upper())
            except ValueError as exc:
                raise ValidationError(f"Unknown processing_status: {status!r}") from exc

        decoded = decode_keyset_cursor(cursor) if cursor else None
        rows = await self.articles.list_page(
            limit=limit, source=source, status=status_enum, cursor=decoded
        )

        next_cursor: str | None = None
        if len(rows) > limit:
            rows = rows[:limit]
            last = rows[-1]
            next_cursor = encode_keyset_cursor(last.created_at, last.id)
        return rows, next_cursor
