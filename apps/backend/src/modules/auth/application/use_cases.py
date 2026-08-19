"""Auth application use cases — register, login, logout."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from core.exceptions import AuthenticationError, ValidationError
from core.logger import get_logger
from core.security import generate_token, hash_password, needs_rehash, verify_password
from modules.auth.domain.entities import Session, User
from modules.auth.domain.repositories import SessionRepository, UserRepository

logger = get_logger(__name__)

MIN_PASSWORD_LENGTH = 8
SESSION_TTL = timedelta(days=7)


class RegisterUseCase:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def execute(self, email: str, password: str, full_name: str = "") -> User:
        if not email or "@" not in email:
            raise ValidationError("Valid email is required")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValidationError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
            )

        existing = await self._user_repo.get_by_email(email)
        if existing:
            raise ValidationError("Email already registered")

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
        )
        return await self._user_repo.create(user)


class LoginUseCase:
    def __init__(self, user_repo: UserRepository, session_repo: SessionRepository):
        self._user_repo = user_repo
        self._session_repo = session_repo

    async def execute(self, email: str, password: str) -> tuple[User, Session]:
        user = await self._user_repo.get_by_email(email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        # Transparently upgrade legacy/weaker hashes on successful login.
        if needs_rehash(user.hashed_password):
            user.hashed_password = hash_password(password)
            await self._user_repo.update(user)
            logger.info("password_hash_upgraded", user_id=str(user.id))

        session = Session(
            user_id=user.id,
            token=generate_token(),
            expires_at=datetime.now(UTC) + SESSION_TTL,
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
