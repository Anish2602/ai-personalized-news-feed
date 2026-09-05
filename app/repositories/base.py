from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    """Holds the unit-of-work session. Repositories never commit — the request
    (``get_db_session``) or task owns the transaction boundary."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
