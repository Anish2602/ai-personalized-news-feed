"""FastAPI dependency providers.

Wires ``AsyncSession -> Repository -> Service`` so routers depend only on
services and never touch the session or SQLAlchemy directly.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.article_repository import ArticleRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.processing_repository import ProcessingRepository
from app.repositories.profile_repository import ProfileRepository
from app.repositories.story_repository import StoryRepository
from app.repositories.user_repository import UserRepository
from app.services.article_service import ArticleService
from app.services.ingestion_service import IngestionService, QueueProcessing
from app.services.interaction_service import InteractionService, QueueProfileRebuild
from app.services.recommendation_service import RecommendationService
from app.services.story_service import StoryService
from app.services.user_service import UserService
from app.vector.client import vector_store

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserRepository(session))


def get_article_service(session: SessionDep) -> ArticleService:
    return ArticleService(ArticleRepository(session))


def get_story_service(session: SessionDep) -> StoryService:
    return StoryService(StoryRepository(session))


def get_queue_profile_rebuild() -> QueueProfileRebuild:
    from app.workers.dispatch import enqueue_profile_rebuild

    return enqueue_profile_rebuild


def get_interaction_service(
    session: SessionDep,
    queue_profile_rebuild: Annotated[
        QueueProfileRebuild, Depends(get_queue_profile_rebuild)
    ],
) -> InteractionService:
    return InteractionService(
        InteractionRepository(session),
        UserRepository(session),
        ArticleRepository(session),
        queue_profile_rebuild,
    )


async def get_recommendation_service(
    session: SessionDep,
) -> AsyncIterator[RecommendationService]:
    async with vector_store() as store:
        yield RecommendationService(
            StoryRepository(session),
            InteractionRepository(session),
            ProfileRepository(session),
            store,
        )


def get_queue_processing() -> QueueProcessing:
    """Seam for enqueuing AI processing — overridden with a spy in tests."""
    from app.workers.dispatch import enqueue_process_article

    return enqueue_process_article


def get_ingestion_service(
    session: SessionDep,
    queue_processing: Annotated[QueueProcessing, Depends(get_queue_processing)],
) -> IngestionService:
    return IngestionService(
        ArticleRepository(session), ProcessingRepository(session), queue_processing
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ArticleServiceDep = Annotated[ArticleService, Depends(get_article_service)]
StoryServiceDep = Annotated[StoryService, Depends(get_story_service)]
RecommendationServiceDep = Annotated[
    RecommendationService, Depends(get_recommendation_service)
]
InteractionServiceDep = Annotated[InteractionService, Depends(get_interaction_service)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
