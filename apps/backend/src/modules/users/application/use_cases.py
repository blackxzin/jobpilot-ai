"""Users application use cases."""
from __future__ import annotations

from typing import Optional

from core.exceptions import NotFoundError
from modules.users.domain.entities import UserProfile
from modules.auth.domain.repositories import UserRepository


class GetProfileUseCase:
    def __init__(self, user_repo: UserRepository):
        self._user_repo = user_repo

    async def execute(self, user_id: str) -> UserProfile:
        user = await self._user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        profile = UserProfile(
            user_id=user.id,
        )
        return profile
