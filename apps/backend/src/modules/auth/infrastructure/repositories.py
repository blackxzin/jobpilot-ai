"""Auth infrastructure — SQLAlchemy repository implementations."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from modules.auth.domain.entities import User, Session
from modules.auth.domain.repositories import UserRepository, SessionRepository
from core.models import UserModel, SessionModel


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self._session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def create(self, user: User) -> User:
        model = UserModel(
            id=str(user.id),
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
        )
        self._session.add(model)
        await self._session.flush()
        user.id = model.id
        return user

    async def update(self, user: User) -> User:
        model = await self._session.get(UserModel, str(user.id))
        if model is None:
            return user
        model.email = user.email
        model.full_name = user.full_name
        model.avatar_url = user.avatar_url
        model.is_active = user.is_active
        model.is_superuser = user.is_superuser
        await self._session.flush()
        return user

    def _to_domain(self, model: UserModel) -> User:
        import uuid
        return User(
            id=uuid.UUID(model.id) if isinstance(model.id, str) else model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            full_name=model.full_name or "",
            avatar_url=model.avatar_url,
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_token(self, token: str) -> Optional[Session]:
        result = await self._session.execute(
            select(SessionModel).where(SessionModel.token == token)
        )
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def create(self, session_obj: Session) -> Session:
        model = SessionModel(
            id=str(session_obj.id),
            user_id=str(session_obj.user_id),
            token=session_obj.token,
            expires_at=session_obj.expires_at,
        )
        self._session.add(model)
        await self._session.flush()
        return session_obj

    async def delete(self, session_id: str) -> None:
        await self._session.execute(
            delete(SessionModel).where(SessionModel.id == session_id)
        )

    async def delete_expired(self) -> int:
        from datetime import datetime, UTC
        result = await self._session.execute(
            delete(SessionModel).where(SessionModel.expires_at < datetime.now(UTC))
        )
        return result.rowcount

    def _to_domain(self, model: SessionModel) -> Session:
        import uuid
        return Session(
            id=uuid.UUID(model.id) if isinstance(model.id, str) else model.id,
            user_id=uuid.UUID(model.user_id) if isinstance(model.user_id, str) else model.user_id,
            token=model.token,
            expires_at=model.expires_at,
            created_at=model.created_at,
        )
