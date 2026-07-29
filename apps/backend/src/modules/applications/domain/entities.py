"""Application domain entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from modules.applications.domain.enums import ApplicationStatus


@dataclass
class Application:
    """Represents a user's application to a job posting."""

    id: UUID = field(default_factory=uuid4)
    job_id: UUID = field(default_factory=uuid4)
    resume_id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    status: ApplicationStatus = ApplicationStatus.APPLIED
    cover_letter: str = ""
    custom_message: str = ""
    applied_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    source_platform: Optional[str] = None
    tracking_data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
