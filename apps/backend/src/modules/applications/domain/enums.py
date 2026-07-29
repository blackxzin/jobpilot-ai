"""Application status enumeration."""
from __future__ import annotations

from enum import Enum


class ApplicationStatus(str, Enum):
    """Represents the lifecycle stages of a job application."""

    APPLIED = "applied"
    UNDER_REVIEW = "under_review"
    TECHNICAL_TEST = "technical_test"
    HR_INTERVIEW = "hr_interview"
    TECHNICAL_INTERVIEW = "technical_interview"
    OFFER = "offer"
    REJECTED = "rejected"

    @classmethod
    def all_values(cls) -> list[str]:
        """Return all status values as strings."""
        return [member.value for member in cls]
