"""Authentication / authorization seam.

Dev-oriented for now: a caller identifies itself with an ``X-User-Id`` header.
The abstraction (``get_current_user_id`` dependency) is deliberately the only
touch-point, so a real JWT bearer scheme can be dropped in later without
changing any service or repository code.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import Header

from app.core.exceptions import AppError


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"
    message = "Authentication required."


async def get_current_user_id(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
) -> UUID:
    """Resolve the authenticated user id.

    Later: replace the header parse with bearer-token decoding + signature
    verification. The return contract (a ``UUID``) stays identical.
    """
    if not x_user_id:
        raise AuthError("Missing X-User-Id header.")
    try:
        return UUID(x_user_id)
    except ValueError as exc:
        raise AuthError("X-User-Id is not a valid UUID.") from exc
