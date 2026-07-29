"""Auth domain repository interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from modules.auth.domain.entities import User, Session


class UserRepository(ABC):
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def get_by_id(self, user_id: str) -> Optional[User]: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def update(self, user: User) -> User: ...


class SessionRepository(ABC):
    @abstractmethod
    async def get_by_token(self, token: str) -> Optional[Session]: ...

    @abstractmethod
    async def create(self, session: Session) -> Session: ...

    @abstractmethod
    async def delete(self, session_id: str) -> None: ...

    @abstractmethod
    async def delete_expired(self) -> int: ...
