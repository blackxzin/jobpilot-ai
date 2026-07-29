"""Resume domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Resume:
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    title: str = ""
    file_url: str = ""
    content_text: str = ""
    ats_score: Optional[int] = None
    ats_breakdown: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
