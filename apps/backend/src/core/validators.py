"""Shared input validators for API boundaries.

Route path/body parameters arrive as raw strings. Passing a malformed UUID
straight to the database raises a driver-level error that surfaces as an
opaque 500, so every route parses identifiers through here and gets a 422
with a useful message instead.
"""
from __future__ import annotations

from uuid import UUID

from core.exceptions import ValidationError


def parse_uuid(value: str, field: str = "id") -> UUID:
    """Return `value` as a UUID, raising ValidationError when malformed."""
    try:
        return UUID(str(value))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValidationError(f"'{field}' must be a valid UUID") from exc


def validate_uuid(value: str, field: str = "id") -> str:
    """Validate a UUID and return it in canonical string form."""
    return str(parse_uuid(value, field))
