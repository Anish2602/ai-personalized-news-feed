"""Article/story enrichment: topic classification + story summarization.

Runs after deduplication in the processing pipeline. Classification always
succeeds (LLM or keyword fallback). Summarization runs once per story (first
article); a later duplicate only merges its topics in.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel

from app.ai.classifier import Classifier
from app.ai.summarizer import Summarizer
from app.core.logging import get_logger
from app.core.metrics import articles_processed_total
from app.db.models.article import Article
from app.repositories.article_repository import ArticleRepository
from app.repositories.story_repository import StoryRepository

logger = get_logger(__name__)


class EnrichmentResult(BaseModel):
    article_topics: list[str]
    story_topics: list[str]
    summarized: bool


class EnrichmentService:
    def __init__(
        self,
        articles: ArticleRepository,
        stories: StoryRepository,
        summarizer: Summarizer,
        classifier: Classifier,
        taxonomy: list[str],
    ) -> None:
        self.articles = articles
        self.stories = stories
        self.summarizer = summarizer
        self.classifier = classifier
        self.taxonomy = taxonomy

    async def enrich(self, article: Article, *, text: str, story_id: UUID) -> EnrichmentResult:
        topics = await self.classifier.classify(title=article.title, text=text)
        await self.articles.set_topics(article.id, topics)

        story = await self.stories.get(story_id)
        merged = sorted({*(story.topics if story else []), *topics})
        summarized = False

        if story is not None and not story.summary:
            result = await self.summarizer.summarize(
                title=article.title, text=text, taxonomy=self.taxonomy
            )
            merged = sorted({*merged, *(t for t in result.topics if t in self.taxonomy)})
            await self.stories.set_enrichment(
                story_id,
                summary=result.summary,
                key_points=result.key_points,
                topics=merged,
            )
            summarized = True
        else:
            await self.stories.set_topics(story_id, merged)

        articles_processed_total.labels(result="enriched").inc()
        logger.info(
            "article_enriched",
            article_id=str(article.id),
            story_id=str(story_id),
            topics=topics,
            summarized=summarized,
        )
        return EnrichmentResult(
            article_topics=topics, story_topics=merged, summarized=summarized
        )
