"""Application domain entity."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
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
    applied_at: datetime | None = None
    responded_at: datetime | None = None
    source_platform: str | None = None
    tracking_data: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
