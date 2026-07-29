"""Application repository interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from modules.applications.domain.entities import Application
from modules.applications.domain.enums import ApplicationStatus


class IApplicationRepository(ABC):
    """Abstract repository contract for application persistence."""

    @abstractmethod
    async def get_by_id(self, application_id: str) -> Optional[Application]:
        """Retrieve a single application by its unique identifier.

        Args:
            application_id: The UUID string of the application.

        Returns:
            The matching Application, or None if not found.
        """

    @abstractmethod
    async def get_for_user(self, user_id: str) -> list[Application]:
        """Retrieve all applications belonging to a user.

        Args:
            user_id: The UUID string of the user.

        Returns:
            A list of applications for the given user, ordered by creation date descending.
        """

    @abstractmethod
    async def get_by_job(self, job_id: str) -> list[Application]:
        """Retrieve all applications submitted for a specific job.

        Args:
            job_id: The UUID string of the job.

        Returns:
            A list of applications for the given job.
        """

    @abstractmethod
    async def create(self, application: Application) -> Application:
        """Persist a new application record.

        Args:
            application: The Application entity to persist.

        Returns:
            The persisted Application with its id populated.
        """

    @abstractmethod
    async def update_status(
        self, application_id: str, status: ApplicationStatus
    ) -> Application:
        """Transition an application to a new status.

        Args:
            application_id: The UUID string of the application.
            status: The new status to set.

        Returns:
            The updated Application entity.

        Raises:
            NotFoundError: If no application exists with the given id.
        """

    @abstractmethod
    async def delete(self, application_id: str) -> None:
        """Remove an application record.

        Args:
            application_id: The UUID string of the application to delete.

        Raises:
            NotFoundError: If no application exists with the given id.
        """

    @abstractmethod
    async def list_by_status(
        self, status: ApplicationStatus
    ) -> list[Application]:
        """Retrieve all applications currently at a given status.

        Args:
            status: The ApplicationStatus to filter by.

        Returns:
            A list of applications matching the given status.
        """
