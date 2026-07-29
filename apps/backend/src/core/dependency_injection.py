"""
JobPilot AI — Dependency Injection Container

Simple DI container that wires up services and repositories.
"""

from __future__ import annotations

from typing import AsyncGenerator, TypeVar, Generic
from contextlib import asynccontextmanager

T = TypeVar("T")


class Container:
    """Simple dependency injection container."""

    _services: dict[type, object] = {}
    _factories: dict[type, callable] = {}

    @classmethod
    def register(cls, service_type: type[T], instance: T) -> None:
        """Register a singleton instance."""
        cls._services[service_type] = instance

    @classmethod
    def register_factory(cls, service_type: type[T], factory: callable) -> None:
        """Register a factory function for a service type."""
        cls._factories[service_type] = factory

    @classmethod
    def resolve(cls, service_type: type[T]) -> T:
        """Resolve a service by type."""
        if service_type in cls._services:
            return cls._services[service_type]
        if service_type in cls._factories:
            instance = cls._factories[service_type]()
            cls._services[service_type] = instance
            return instance
        raise KeyError(f"Service {service_type.__name__} not registered")

    @classmethod
    def clear(cls) -> None:
        """Clear all registered services (useful for testing)."""
        cls._services.clear()
        cls._factories.clear()


@asynccontextmanager
async def lifespan_context(app):
    """Initialize and tear down the DI container."""
    # Startup: resolve services that need initialization
    # TODO: register database session, Redis connection, LLM providers, etc.
    yield
    # Shutdown: clean up
    Container.clear()
