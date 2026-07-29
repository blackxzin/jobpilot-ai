"""Jobs domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class Job:
    id: UUID = field(default_factory=uuid4)
    source: str = "manual"
    title: str = ""
    company_name: str = ""
    company_id: Optional[UUID] = None
    description: str = ""
    responsibilities: str = ""
    seniority: str = ""
    location: str = ""
    location_type: str = ""
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    currency: str = "BRL"
    apply_url: str = ""
    source_url: str = ""
    posted_at: Optional[datetime] = None
    is_remote: bool = False
    metadata_json: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
