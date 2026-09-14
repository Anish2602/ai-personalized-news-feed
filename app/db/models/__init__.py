"""Import every model so ``Base.metadata`` is complete for Alembic autogenerate."""

from app.db.base import Base
from app.db.models.article import Article, ArticleProcessingStatus
from app.db.models.interaction import Interaction, InteractionType
from app.db.models.processing import ProcessingJob, ProcessingJobStatus
from app.db.models.profile import UserProfile
from app.db.models.story import Story
from app.db.models.user import Interest, User, UserInterest

__all__ = [
    "Base",
    "Article",
    "ArticleProcessingStatus",
    "Interaction",
    "InteractionType",
    "ProcessingJob",
    "ProcessingJobStatus",
    "Story",
    "Interest",
    "User",
    "UserInterest",
    "UserProfile",
]
