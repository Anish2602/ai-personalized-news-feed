"""FastAPI dependency providers.

Wires ``AsyncSession -> Repository -> Service`` so routers depend only on
services and never touch the session or SQLAlchemy directly.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.repositories.article_repository import ArticleRepository
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.user_repository import UserRepository
from app.services.article_service import ArticleService
from app.services.interaction_service import InteractionService
from app.services.user_service import UserService

SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserRepository(session))


def get_article_service(session: SessionDep) -> ArticleService:
    return ArticleService(ArticleRepository(session))


def get_interaction_service(session: SessionDep) -> InteractionService:
    return InteractionService(
        InteractionRepository(session),
        UserRepository(session),
        ArticleRepository(session),
    )


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
ArticleServiceDep = Annotated[ArticleService, Depends(get_article_service)]
InteractionServiceDep = Annotated[InteractionService, Depends(get_interaction_service)]
