"""
JobPilot AI — Custom Exceptions

Domain-specific exception hierarchy for consistent error responses.
"""

from __future__ import annotations


class JobPilotException(Exception):
    """Base exception for all JobPilot errors."""

    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(message)


class NotFoundError(JobPilotException):
    """Resource not found."""


class ValidationError(JobPilotException):
    """Input validation failed."""


class AuthenticationError(JobPilotException):
    """Authentication failed or missing."""


class AuthorizationError(JobPilotException):
    """User does not have permission."""


class LLMProviderError(JobPilotException):
    """Error from an LLM provider."""


class JobSourceError(JobPilotException):
    """Error from a job board source."""


class ScrapingError(JobPilotException):
    """Error during scraping operation."""


class ConfigurationError(JobPilotException):
    """Misconfigured service or provider."""
