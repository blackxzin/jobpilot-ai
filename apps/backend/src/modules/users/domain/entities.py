"""Users domain entities and repositories."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class UserProfile:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    headline: str = ""
    bio: str = ""
    phone: str = ""
    location: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    portfolio_url: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
