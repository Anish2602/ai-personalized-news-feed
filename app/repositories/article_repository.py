from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select

from app.db.models.article import Article, ArticleProcessingStatus
from app.repositories.base import BaseRepository


class ArticleRepository(BaseRepository):
    async def get(self, article_id: UUID) -> Article | None:
        return await self.session.get(Article, article_id)

    async def get_by_url(self, url: str) -> Article | None:
        result = await self.session.execute(select(Article).where(Article.url == url))
        return result.scalar_one_or_none()

    async def list_page(
        self,
        *,
        limit: int,
        source: str | None = None,
        status: ArticleProcessingStatus | None = None,
        cursor: tuple[datetime, str] | None = None,
    ) -> list[Article]:
        """Keyset page ordered by ``(created_at DESC, id DESC)``.

        Fetches ``limit + 1`` so the service can tell whether another page
        exists without a second COUNT query.
        """
        stmt = select(Article)
        if source is not None:
            stmt = stmt.where(Article.source == source)
        if status is not None:
            stmt = stmt.where(Article.processing_status == status)
        if cursor is not None:
            cur_ts, cur_id = cursor
            stmt = stmt.where(
                or_(
                    Article.created_at < cur_ts,
                    and_(Article.created_at == cur_ts, Article.id < cur_id),
                )
            )
        stmt = stmt.order_by(Article.created_at.desc(), Article.id.desc()).limit(limit + 1)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(
        self,
        *,
        title: str,
        url: str,
        source: str,
        description: str | None = None,
        content: str | None = None,
        published_at: datetime | None = None,
        story_id: UUID | None = None,
    ) -> Article:
        article = Article(
            title=title,
            url=url,
            source=source,
            description=description,
            content=content,
            published_at=published_at,
            story_id=story_id,
        )
        self.session.add(article)
        await self.session.flush()
        return article
