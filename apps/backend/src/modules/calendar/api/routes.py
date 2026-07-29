"""Calendar API routes — entrevistas e eventos."""
from __future__ import annotations

from datetime import datetime, UTC
from typing import Optional
from fastapi import APIRouter, Depends, Header, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.models import CalendarEventModel
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase

router = APIRouter(prefix="/calendar", tags=["calendar"])


class EventCreate(BaseModel):
    title: str
    event_type: str = "interview"
    date: str = ""
    notes: str = ""
    location: str = ""


class EventUpdate(BaseModel):
    title: Optional[str] = None
    event_type: Optional[str] = None
    date: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None


@router.get("")
async def list_events(
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    result = await db.execute(
        select(CalendarEventModel)
        .where(CalendarEventModel.user_id == str(user.id))
        .order_by(CalendarEventModel.date.asc().nulls_last())
    )
    events = result.scalars().all()
    return {
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "event_type": e.event_type,
                "date": str(e.date) if e.date else "",
                "notes": e.notes or "",
                "location": e.location or "",
                "status": e.status or "scheduled",
            }
            for e in events
        ]
    }


@router.post("")
async def create_event(
    body: EventCreate,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    import uuid
    from datetime import datetime

    event_date = None
    if body.date:
        try:
            event_date = datetime.fromisoformat(body.date.replace("Z", "+00:00"))
        except:
            event_date = None

    event = CalendarEventModel(
        id=str(uuid.uuid4()),
        user_id=str(user.id),
        title=body.title,
        event_type=body.event_type,
        date=event_date,
        notes=body.notes,
        location=body.location,
        status="scheduled",
    )
    db.add(event)
    await db.commit()

    return {
        "id": event.id,
        "title": event.title,
        "event_type": event.event_type,
        "date": str(event.date) if event.date else "",
        "notes": event.notes or "",
        "location": event.location or "",
        "status": event.status,
    }


@router.patch("/{event_id}")
async def update_event(
    event_id: str,
    body: EventUpdate,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    event = await db.get(CalendarEventModel, event_id)
    if not event or str(event.user_id) != str(user.id):
        return {"error": "Event not found"}

    if body.title is not None:
        event.title = body.title
    if body.event_type is not None:
        event.event_type = body.event_type
    if body.date is not None:
        try:
            event.date = datetime.fromisoformat(body.date.replace("Z", "+00:00"))
        except:
            pass
    if body.notes is not None:
        event.notes = body.notes
    if body.location is not None:
        event.location = body.location
    if body.status is not None:
        event.status = body.status

    await db.commit()
    return {"message": "Event updated"}


@router.delete("/{event_id}")
async def delete_event(
    event_id: str,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    event = await db.get(CalendarEventModel, event_id)
    if not event or str(event.user_id) != str(user.id):
        return {"error": "Event not found"}

    await db.delete(event)
    await db.commit()
    return {"message": "Event deleted"}
