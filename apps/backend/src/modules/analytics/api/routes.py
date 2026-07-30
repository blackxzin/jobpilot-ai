"""Analytics API routes — dashboard data, charts, insights."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, text

from core.database import get_db
from core.models import ApplicationModel, JobModel, CompanyModel, InterviewModel, ResumeModel
from modules.auth.infrastructure.repositories import SQLAlchemyUserRepository, SQLAlchemySessionRepository
from modules.auth.application.use_cases import GetCurrentUserUseCase

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(authorization: str = Header(""), db: AsyncSession = Depends(get_db)):
    token = authorization.replace("Bearer ", "")
    user_repo = SQLAlchemyUserRepository(db)
    session_repo = SQLAlchemySessionRepository(db)
    auth_uc = GetCurrentUserUseCase(user_repo, session_repo)
    user = await auth_uc.execute(token)

    uid = str(user.id)

    # Total applications & by status
    total_apps = await db.scalar(select(func.count()).where(ApplicationModel.user_id == uid))

    # Interview rate: apps that reached interview stage
    interviewed = await db.scalar(
        select(func.count()).where(
            ApplicationModel.user_id == uid,
            ApplicationModel.status.in_(["hr_interview", "technical_interview", "offer"]),
        )
    )
    interview_rate = round((interviewed / total_apps * 100), 1) if total_apps and total_apps > 0 else 0

    # Offer rate
    offers = await db.scalar(
        select(func.count()).where(
            ApplicationModel.user_id == uid,
            ApplicationModel.status == "offer",
        )
    )
    offer_rate = round((offers / total_apps * 100), 1) if total_apps and total_apps > 0 else 0

    # Rejection rate
    rejected = await db.scalar(
        select(func.count()).where(
            ApplicationModel.user_id == uid,
            ApplicationModel.status == "rejected",
        )
    )
    rejection_rate = round((rejected / total_apps * 100), 1) if total_apps and total_apps > 0 else 0

    # Response rate (any status change from applied)
    responded = await db.scalar(
        select(func.count()).where(
            ApplicationModel.user_id == uid,
            ApplicationModel.status != "applied",
        )
    )
    response_rate = round((responded / total_apps * 100), 1) if total_apps and total_apps > 0 else 0

    # Top companies (from jobs applied to)
    top_companies_query = (
        select(CompanyModel.name, func.count().label("cnt"))
        .select_from(ApplicationModel)
        .join(JobModel, ApplicationModel.job_id == JobModel.id)
        .join(CompanyModel, JobModel.company_id == CompanyModel.id)
        .where(ApplicationModel.user_id == uid)
        .group_by(CompanyModel.name)
        .order_by(func.count().desc())
        .limit(10)
    )
    result = await db.execute(top_companies_query)
    top_companies = [{"name": row[0], "count": row[1]} for row in result]

    # Applications over time (last 30 days)
    from datetime import datetime, timedelta, UTC
    thirty_days_ago = datetime.now(UTC) - timedelta(days=30)
    time_query = (
        select(
            func.date(ApplicationModel.created_at).label("day"),
            func.count().label("cnt"),
        )
        .where(
            ApplicationModel.user_id == uid,
            ApplicationModel.created_at >= thirty_days_ago,
        )
        .group_by(func.date(ApplicationModel.created_at))
        .order_by(func.date(ApplicationModel.created_at))
    )
    result = await db.execute(time_query)
    apps_over_time = [{"date": str(row[0]), "count": row[1]} for row in result]

    # Top skills from resumes
    skills_query = "SELECT name, COUNT(*) as cnt FROM skills WHERE resume_id IN (SELECT id FROM resumes WHERE user_id = :uid) GROUP BY name ORDER BY cnt DESC LIMIT 20"
    skills_result = await db.execute(text(skills_query), {"uid": uid})
    top_skills = [{"name": row[0], "count": row[1]} for row in skills_result]

    # ATS score average
    avg_ats = await db.scalar(
        select(func.avg(ResumeModel.ats_score)).where(
            ResumeModel.user_id == uid,
            ResumeModel.ats_score.isnot(None),
        )
    )

    return {
        "total_applications": total_apps or 0,
        "interview_rate": interview_rate,
        "offer_rate": offer_rate,
        "rejection_rate": rejection_rate,
        "response_rate": response_rate,
        "interviews": interviewed or 0,
        "offers": offers or 0,
        "rejected": rejected or 0,
        "avg_ats_score": round(avg_ats, 1) if avg_ats else None,
        "top_companies": top_companies[:5],
        "applications_over_time": apps_over_time,
        "top_skills": top_skills[:10],
    }
