"""Semantic (stage-2) deduplication.

For each new article: embed → search Qdrant for the nearest existing article →
if cosine similarity ≥ ``SEMANTIC_DUPLICATE_THRESHOLD`` attach it to that
article's story (creating the story if the neighbour has none), else start a new
story. The new article's vector is then upserted so it can match future ones.

The threshold is configurable and **should be evaluated against real data** —
0.90 is a starting point, not a proven optimum. It trades false merges (too low)
against missed duplicates (too high) and depends on the embedding model.

PostgreSQL is the source of truth for ``story_id``; the Qdrant payload copy is
for debugging only and is never read back to make grouping decisions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.ai.embeddings.base import EmbeddingProvider
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.metrics import duplicate_articles_total
from app.db.models.article import Article
from app.repositories.article_repository import ArticleRepository
from app.repositories.story_repository import StoryRepository
from app.vector.search import VectorStoreProtocol

logger = get_logger(__name__)


class DeduplicationResult(BaseModel):
    story_id: UUID
    is_duplicate: bool
    matched_article_id: UUID | None = None
    similarity: float | None = None


class DeduplicationService:
    def __init__(
        self,
        articles: ArticleRepository,
        stories: StoryRepository,
        vectors: VectorStoreProtocol,
        embedder: EmbeddingProvider,
        *,
        threshold: float | None = None,
        top_k: int | None = None,
    ) -> None:
        settings = get_settings()
        self.articles = articles
        self.stories = stories
        self.vectors = vectors
        self.embedder = embedder
        self.threshold = settings.semantic_duplicate_threshold if threshold is None else threshold
        self.top_k = settings.dedup_top_k if top_k is None else top_k

    async def deduplicate(self, article: Article, *, text: str) -> DeduplicationResult:
        vector = await self.embedder.embed_text(text)
        matches = await self.vectors.search(vector, limit=self.top_k, exclude_id=str(article.id))
        best = matches[0] if matches else None

        if best is not None and best.score >= self.threshold:
            story_id = await self._story_for_match(best.payload, fallback_title=article.title)
            result = DeduplicationResult(
                story_id=story_id,
                is_duplicate=True,
                matched_article_id=_payload_article_id(best.payload),
                similarity=best.score,
            )
            duplicate_articles_total.labels(stage="semantic").inc()
            logger.info(
                "semantic_duplicate",
                article_id=str(article.id),
                story_id=str(story_id),
                similarity=round(best.score, 4),
            )
        else:
            story = await self.stories.create(canonical_title=article.title)
            result = DeduplicationResult(
                story_id=story.id,
                is_duplicate=False,
                similarity=best.score if best else None,
            )
            logger.info("new_story", article_id=str(article.id), story_id=str(story.id))

        await self.articles.assign_story(article.id, result.story_id)
        await self.articles.set_embedding_reference(article.id, str(article.id))
        await self.vectors.upsert(
            str(article.id),
            vector,
            {
                "article_id": str(article.id),
                "story_id": str(result.story_id),
                "source": article.source,
                "published_at": article.published_at.isoformat() if article.published_at else None,
            },
        )
        return result

    async def _story_for_match(self, payload: dict, *, fallback_title: str) -> UUID:
        matched_id = _payload_article_id(payload)
        matched = await self.articles.get(matched_id) if matched_id else None
        if matched is not None and matched.story_id is not None:
            return matched.story_id

        title = matched.title if matched is not None else fallback_title
        story = await self.stories.create(canonical_title=title)
        if matched is not None and matched.story_id is None:
            await self.articles.assign_story(matched.id, story.id)
        return story.id


def _payload_article_id(payload: dict) -> UUID | None:
    raw = payload.get("article_id")
    try:
        return UUID(raw) if raw else None
    except (ValueError, TypeError):
        return None
