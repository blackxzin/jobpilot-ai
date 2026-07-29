"""Cover letters domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class CoverLetter:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    job_id: Optional[UUID] = None
    content: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
