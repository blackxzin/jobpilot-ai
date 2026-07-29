"""Auth application use cases — register, login, logout."""
from __future__ import annotations

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta, UTC

from core.exceptions import AuthenticationError, ValidationError
from core.config import settings

from modules.auth.domain.entities import User, Session
from modules.auth.domain.repositories import UserRepository, SessionRepository


class RegisterUseCase:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def execute(self, email: str, password: str, full_name: str = "") -> User:
        if not email or "@" not in email:
            raise ValidationError("Valid email is required")
        if len(password) < 8:
            raise ValidationError("Password must be at least 8 characters")

        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise ValidationError("Email already registered")

        user = User(
            email=email,
            hashed_password=self._hash_password(password),
            full_name=full_name,
        )
        return await self._user_repo.create(user)

    def _hash_password(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()


class LoginUseCase:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self._user_repo = user_repo
        self._session_repo = session_repo

    async def execute(self, email: str, password: str) -> tuple[User, Session]:
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        hashed = hashlib.sha256(password.encode()).hexdigest()
        if user.hashed_password != hashed:
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        token = secrets.token_urlsafe(48)
        session = Session(
            user_id=user.id,
            token=token,
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        created = await self._session_repo.create(session)
        return user, created


class LogoutUseCase:
    def __init__(self, session_repo: SessionRepository):
        self._session_repo = session_repo

    async def execute(self, token: str) -> None:
        session = await self._session_repo.get_by_token(token)
        if session:
            await self._session_repo.delete(str(session.id))


class GetCurrentUserUseCase:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self._user_repo = user_repo
        self._session_repo = session_repo

    async def execute(self, token: str) -> User:
        if not token:
            raise AuthenticationError("Not authenticated")
        session = await self._session_repo.get_by_token(token)
        if not session:
            raise AuthenticationError("Invalid session")
        now = datetime.now(UTC)
        expires = session.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if expires < now:
            raise AuthenticationError("Session expired")
        user = await self._user_repo.get_by_id(str(session.user_id))
        if not user:
            raise AuthenticationError("User not found")
        return user


class GetSessionUseCase:
    def __init__(self, session_repo: SessionRepository):
        self._session_repo = session_repo

    async def execute(self, token: str) -> Session | None:
        return await self._session_repo.get_by_token(token)
