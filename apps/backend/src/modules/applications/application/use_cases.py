"""Application use cases."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4

from core.exceptions import NotFoundError, ValidationError

from modules.applications.domain.entities import Application
from modules.applications.domain.enums import ApplicationStatus
from modules.applications.domain.repositories import IApplicationRepository


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------


@dataclass
class CreateApplicationDTO:
    """Parameters for creating a new application."""

    job_id: UUID
    resume_id: UUID
    user_id: UUID
    cover_letter: Optional[str] = None
    custom_message: Optional[str] = None
    source_platform: Optional[str] = None
    tracking_data: Optional[dict] = None


@dataclass
class UpdateStatusDTO:
    """Parameters for updating an application status."""

    status: ApplicationStatus


@dataclass
class ApplicationFilters:
    """Optional filters when listing applications."""

    user_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    status: Optional[ApplicationStatus] = None
    source_platform: Optional[str] = None


@dataclass
class ApplicationStats:
    """Aggregate counts of applications grouped by status."""

    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Use Cases
# ---------------------------------------------------------------------------


class CreateApplicationUseCase:
    """Creates a new job application.

    Validates that required fields are present and sets the initial
    status to ``ApplicationStatus.APPLIED``.
    """

    def __init__(self, repository: IApplicationRepository) -> None:
        self._repository = repository

    async def execute(self, dto: CreateApplicationDTO) -> Application:
        """Run the use case.

        Args:
            dto: Data transfer object with application details.

        Returns:
            The newly created Application entity.

        Raises:
            ValidationError: If required fields are missing.
        """
        if not dto.job_id:
            raise ValidationError("job_id is required")
        if not dto.resume_id:
            raise ValidationError("resume_id is required")
        if not dto.user_id:
            raise ValidationError("user_id is required")

        now = datetime.now(UTC)

        application = Application(
            id=uuid4(),
            job_id=dto.job_id,
            resume_id=dto.resume_id,
            user_id=dto.user_id,
            status=ApplicationStatus.APPLIED,
            cover_letter=dto.cover_letter or "",
            custom_message=dto.custom_message or "",
            applied_at=now,
            source_platform=dto.source_platform,
            tracking_data=dto.tracking_data or {},
            created_at=now,
            updated_at=now,
        )

        return await self._repository.create(application)


class UpdateApplicationStatusUseCase:
    """Updates the status of an existing application."""

    def __init__(self, repository: IApplicationRepository) -> None:
        self._repository = repository

    async def execute(
        self, application_id: str, dto: UpdateStatusDTO
    ) -> Application:
        """Run the use case.

        Args:
            application_id: The UUID string of the application.
            dto: Data transfer object containing the new status.

        Returns:
            The updated Application entity.

        Raises:
            NotFoundError: If no application exists with the given id.
        """
        application = await self._repository.get_by_id(application_id)
        if application is None:
            raise NotFoundError(
                f"Application with id {application_id} not found"
            )

        application.status = dto.status
        application.updated_at = datetime.now(UTC)

        if dto.status in (
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
        ) and application.responded_at is None:
            application.responded_at = application.updated_at

        return await self._repository.update_status(
            application_id, dto.status
        )


class GetUserApplicationsUseCase:
    """Lists all applications for a user with optional filters."""

    def __init__(self, repository: IApplicationRepository) -> None:
        self._repository = repository

    async def execute(
        self,
        user_id: str,
        status: Optional[str] = None,
        source_platform: Optional[str] = None,
    ) -> list[Application]:
        """Run the use case.

        Args:
            user_id: The UUID string of the user.
            status: Optional status filter.
            source_platform: Optional source platform filter.

        Returns:
            A list of applications matching the criteria.
        """
        if status:
            try:
                status_enum = ApplicationStatus(status)
            except ValueError:
                status_enum = None
        else:
            status_enum = None

        applications = await self._repository.get_for_user(user_id)

        if status_enum:
            applications = [a for a in applications if a.status == status_enum]

        if source_platform:
            applications = [
                a
                for a in applications
                if (a.source_platform or "").lower()
                == source_platform.lower()
            ]

        return applications


class GetApplicationStatsUseCase:
    """Returns aggregate statistics about applications."""

    def __init__(self, repository: IApplicationRepository) -> None:
        self._repository = repository

    async def execute(self, user_id: Optional[str] = None) -> ApplicationStats:
        """Run the use case.

        Args:
            user_id: Optional user filter. When provided, stats are
                scoped to that user only.

        Returns:
            An ApplicationStats instance with counts per status.
        """
        if user_id:
            applications = await self._repository.get_for_user(user_id)
        else:
            applications = []
            for status in ApplicationStatus:
                apps = await self._repository.list_by_status(status)
                applications.extend(apps)

        stats = ApplicationStats(total=len(applications))
        for app in applications:
            value = app.status.value if hasattr(app.status, "value") else app.status
            stats.by_status[value] = stats.by_status.get(value, 0) + 1

        return stats
