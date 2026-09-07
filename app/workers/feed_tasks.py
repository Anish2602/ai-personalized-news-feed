"""Feed-related background tasks."""

from __future__ import annotations

from uuid import UUID

from app.core.logging import bind_context, clear_context, get_logger
from app.core.metrics import worker_failures_total
from app.repositories.interaction_repository import InteractionRepository
from app.repositories.profile_repository import ProfileRepository
from app.services.profile_service import ProfileService
from app.vector.client import vector_store
from app.workers.celery_app import celery_app
from app.workers.runtime import run_with_session

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.feed_tasks.rebuild_user_profile",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    acks_late=True,
)
def rebuild_user_profile(self, user_id: str) -> dict[str, object]:
    """Recompute the user's interest vector from their recent interactions.

    Idempotent — the result depends only on stored interactions + article
    vectors, so a duplicate run produces the same profile.
    """
    bind_context(task_id=self.request.id, user_id=user_id)
    uid = UUID(user_id)
    try:

        async def _op(session):
            async with vector_store() as store:
                service = ProfileService(
                    InteractionRepository(session), ProfileRepository(session), store
                )
                result = await service.rebuild(uid)
                return result.model_dump(mode="json")

        return run_with_session(_op)
    except Exception as exc:
        worker_failures_total.labels(task="rebuild_user_profile").inc()
        logger.exception("rebuild_user_profile_failed", error=str(exc))
        raise self.retry(exc=exc, countdown=self.default_retry_delay) from exc
    finally:
        clear_context()
