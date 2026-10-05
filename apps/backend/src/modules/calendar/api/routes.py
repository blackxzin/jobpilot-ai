"""Calendar API routes — entrevistas e eventos."""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.exceptions import NotFoundError, ValidationError
from core.models import CalendarEventModel
from core.validators import validate_uuid
from modules.auth.api.dependencies import get_current_user
from modules.auth.domain.entities import User

router = APIRouter(prefix="/calendar", tags=["calendar"])


class EventCreate(BaseModel):
    title: str
    event_type: str = "interview"
    date: str = ""
    notes: str = ""
    location: str = ""


class EventUpdate(BaseModel):
    title: str | None = None
    event_type: str | None = None
    date: str | None = None
    notes: str | None = None
    location: str | None = None
    status: str | None = None


def _parse_date(value: str) -> datetime | None:
    """Parse an ISO-8601 date, rejecting malformed input with a 422."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValidationError(f"Invalid ISO-8601 date: '{value}'") from e


def _event_to_dict(e: CalendarEventModel) -> dict:
    return {
        "id": e.id,
        "title": e.title,
        "event_type": e.event_type,
        "date": str(e.date) if e.date else "",
        "notes": e.notes or "",
        "location": e.location or "",
        "status": e.status or "scheduled",
    }


async def _get_owned_event(db: AsyncSession, event_id: str, user: User) -> CalendarEventModel:
    event = await db.get(CalendarEventModel, validate_uuid(event_id, "event_id"))
    if not event or str(event.user_id) != str(user.id):
        raise NotFoundError("Event not found")
    return event


@router.get("")
async def list_events(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CalendarEventModel)
        .where(CalendarEventModel.user_id == str(user.id))
        .order_by(CalendarEventModel.date.asc().nulls_last())
    )
    return {"events": [_event_to_dict(e) for e in result.scalars().all()]}


@router.post("")
async def create_event(
    body: EventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not body.title.strip():
        raise ValidationError("title is required")

    event = CalendarEventModel(
        id=str(uuid.uuid4()),
        user_id=str(user.id),
        title=body.title,
        event_type=body.event_type,
        date=_parse_date(body.date),
        notes=body.notes,
        location=body.location,
        status="scheduled",
    )
    db.add(event)
    await db.flush()
    return _event_to_dict(event)


@router.patch("/{event_id}")
async def update_event(
    event_id: str,
    body: EventUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await _get_owned_event(db, event_id, user)

    if body.title is not None:
        event.title = body.title
    if body.event_type is not None:
        event.event_type = body.event_type
    if body.date is not None:
        event.date = _parse_date(body.date)
    if body.notes is not None:
        event.notes = body.notes
    if body.location is not None:
        event.location = body.location
    if body.status is not None:
        event.status = body.status

    await db.flush()
    return _event_to_dict(event)


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    event = await _get_owned_event(db, event_id, user)
    await db.delete(event)
    await db.flush()
    return {"message": "Event deleted"}
