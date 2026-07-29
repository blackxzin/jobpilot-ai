"""
JobPilot AI — Structured Logging

Uses structlog for JSON-formatted, context-aware logging.
"""

import sys
from typing import Any

import structlog


def add_log_level(logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Processor that adds the log level to the event dict."""
    return event_dict


def add_timestamp(logger: Any, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Processor that adds a timestamp."""
    from datetime import datetime, timezone
    event_dict["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog with JSON output for production, pretty output for dev."""
    processors = [
        structlog.contextvars.merge_context_vars,
        structlog.processors.add_log_level,
        add_timestamp,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if log_level == "DEBUG":
        # Human-readable output in development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), log_level.upper(), __import__("logging").INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str):
    """Return a configured structlog logger."""
    return structlog.get_logger(name)


# Auto-configure on import
configure_logging()
