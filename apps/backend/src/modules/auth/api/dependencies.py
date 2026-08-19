"""Shared authentication dependencies for API routes.

Centralizes the "resolve the current user from the Authorization header"
logic that every protected route needs, so routes stay short and the
authorization rules live in a single place.
"""
from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError
from modules.auth.application.use_cases import GetCurrentUserUseCase
from modules.auth.domain.entities import User
from modules.auth.infrastructure.repositories import (
    SQLAlchemySessionRepository,
    SQLAlchemyUserRepository,
)

BEARER_PREFIX = "Bearer "


def extract_bearer_token(authorization: str) -> str:
    """Return the raw token from an Authorization header value."""
    value = (authorization or "").strip()
    if value.lower().startswith(BEARER_PREFIX.lower()):
        return value[len(BEARER_PREFIX):].strip()
    return value


async def get_current_user(
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the authenticated user, raising AuthenticationError if invalid."""
    use_case = GetCurrentUserUseCase(
        SQLAlchemyUserRepository(db),
        SQLAlchemySessionRepository(db),
    )
    return await use_case.execute(extract_bearer_token(authorization))


def ensure_owner(owner_id, user: User, resource: str = "Resource") -> None:
    """Raise NotFoundError when `user` does not own the resource.

    404 (rather than 403) is deliberate: it avoids leaking the existence of
    resources belonging to other users.
    """
    if str(owner_id) != str(user.id):
        raise NotFoundError(f"{resource} not found")
