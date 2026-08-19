"""Jobs domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass
class Job:
    id: UUID = field(default_factory=uuid4)
    source: str = "manual"
    title: str = ""
    company_name: str = ""
    company_id: UUID | None = None
    description: str = ""
    responsibilities: str = ""
    seniority: str = ""
    location: str = ""
    location_type: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = "BRL"
    apply_url: str = ""
    source_url: str = ""
    posted_at: datetime | None = None
    is_remote: bool = False
    metadata_json: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
