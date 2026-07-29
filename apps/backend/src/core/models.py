"""JobPilot AI — All SQLAlchemy ORM models (centralized for modular monolith)."""
from __future__ import annotations

import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, DateTime, ForeignKey, Enum as SAEnum, JSON, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from core.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


# ── Auth / Users ────────────────────────────────────────────────────────────

class UserModel(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    avatar_url = Column(String(512), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    settings = relationship("UserSettingsModel", uselist=False, back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("ResumeModel", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationModel", back_populates="user", cascade="all, delete-orphan")


class UserSettingsModel(Base):
    __tablename__ = "user_settings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    theme = Column(String(20), default="system")
    language = Column(String(10), default="pt-BR")
    notifications_enabled = Column(Boolean, default=True)

    user = relationship("UserModel", back_populates="settings")


class SessionModel(Base):
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(512), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── LLM Provider Config ─────────────────────────────────────────────────────

class LLMProviderConfigModel(Base):
    __tablename__ = "llm_provider_configs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_name = Column(String(50), nullable=False)  # openai, anthropic, gemini, ollama, nvidia_nim, openrouter
    api_key_encrypted = Column(Text, default="")
    base_url = Column(String(512), default="")
    model = Column(String(128), default="gpt-4o")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "provider_name", name="uq_user_provider"),
    )


# ── Resume ──────────────────────────────────────────────────────────────────

class ResumeModel(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="")
    file_url = Column(String(512), default="")
    content_text = Column(Text, default="")
    ats_score = Column(Integer, nullable=True)
    ats_breakdown = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("UserModel", back_populates="resumes")
    experiences = relationship("ExperienceModel", back_populates="resume", cascade="all, delete-orphan")
    skills = relationship("SkillModel", back_populates="resume", cascade="all, delete-orphan")


class ExperienceModel(Base):
    __tablename__ = "experiences"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    resume_id = Column(UUID(as_uuid=False), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), default="")
    role = Column(String(255), default="")
    description = Column(Text, default="")
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    resume = relationship("ResumeModel", back_populates="experiences")


class SkillModel(Base):
    __tablename__ = "skills"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    resume_id = Column(UUID(as_uuid=False), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(128), nullable=False)
    category = Column(String(64), default="")
    level = Column(String(32), default="intermediate")  # beginner, intermediate, advanced, expert

    resume = relationship("ResumeModel", back_populates="skills")


# ── Companies ──────────────────────────────────────────────────────────────

class CompanyModel(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False, index=True)
    website = Column(String(512), default="")
    industry = Column(String(128), default="")
    location = Column(String(255), default="")
    logo_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    jobs = relationship("JobModel", back_populates="company", cascade="all, delete-orphan")


# ── Jobs ────────────────────────────────────────────────────────────────────

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    source = Column(String(50), default="manual")  # manual, gupy, indeed, linkedin
    source_id = Column(String(255), nullable=True)  # ID from external source
    title = Column(String(255), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=False), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True)
    description = Column(Text, default="")
    responsibilities = Column(Text, default="")
    seniority = Column(String(50), default="")
    location = Column(String(255), default="")
    location_type = Column(String(20), default="")  # remote, hybrid, onsite
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    currency = Column(String(10), default="BRL")
    apply_url = Column(String(512), default="")
    source_url = Column(String(512), default="")
    posted_at = Column(DateTime(timezone=True), nullable=True)
    is_remote = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    company = relationship("CompanyModel", back_populates="jobs")
    requirements = relationship("JobRequirementModel", back_populates="job", cascade="all, delete-orphan")
    matches = relationship("JobMatchModel", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_jobs_source_posted", "source", "posted_at"),
    )


class JobRequirementModel(Base):
    __tablename__ = "job_requirements"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement = Column(String(255), nullable=False)
    is_must_have = Column(Boolean, default=True)
    category = Column(String(64), default="")

    job = relationship("JobModel", back_populates="requirements")


class JobMatchModel(Base):
    __tablename__ = "job_matches"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(UUID(as_uuid=False), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, default=0.0)
    match_reasons = Column(JSON, default=list)
    suggestions = Column(JSON, default=list)
    matched_skills = Column(JSON, default=list)
    missing_skills = Column(JSON, default=list)
    score_details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    job = relationship("JobModel", back_populates="matches")


# ── Applications ────────────────────────────────────────────────────────────

class ApplicationModel(Base):
    __tablename__ = "applications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(UUID(as_uuid=False), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), default="applied")  # applied, under_review, technical_test, hr_interview, technical_interview, offer, rejected
    cover_letter = Column(Text, default="")
    custom_message = Column(Text, default="")
    applied_at = Column(DateTime(timezone=True), nullable=True)
    responded_at = Column(DateTime(timezone=True), nullable=True)
    source_platform = Column(String(50), nullable=True)
    tracking_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("UserModel", back_populates="applications")
    interviews = relationship("InterviewModel", back_populates="application", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_applications_user_status", "user_id", "status"),
    )


class InterviewModel(Base):
    __tablename__ = "interviews"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    application_id = Column(UUID(as_uuid=False), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), default="")  # hr, technical, behavioral, final
    date = Column(DateTime(timezone=True), nullable=True)
    company = Column(String(255), default="")
    stage = Column(String(50), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    application = relationship("ApplicationModel", back_populates="interviews")


# ── Cover Letters ───────────────────────────────────────────────────────────

class CoverLetterModel(Base):
    __tablename__ = "cover_letters"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=False), ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── AI Analysis ─────────────────────────────────────────────────────────────

class AIAnalysisModel(Base):
    __tablename__ = "ai_analyses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    analyzable_type = Column(String(50), default="")  # resume, job, application
    analyzable_id = Column(String(128), default="")
    analysis_type = Column(String(50), default="")  # ats_score, matching, cover_letter, summary
    result = Column(JSON, default=dict)
    score = Column(Float, nullable=True)
    tokens_used = Column(Integer, default=0)
    model_used = Column(String(128), default="")
    provider_used = Column(String(50), default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Notifications ───────────────────────────────────────────────────────────

class NotificationModel(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(30), default="email")  # email, discord, telegram, push
    title = Column(String(255), default="")
    message = Column(Text, default="")
    channel = Column(String(30), default="email")  # email, discord, telegram, push
    status = Column(String(20), default="pending")  # pending, sent, failed, read
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Calendar Events ─────────────────────────────────────────────────────────

class CalendarEventModel(Base):
    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="")
    event_type = Column(String(50), default="")  # interview, deadline, reminder
    date = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, default="")
    location = Column(String(255), default="")
    status = Column(String(20), default="scheduled")
    created_at = Column(DateTime(timezone=True), default=_utcnow)


# ── Search Preferences ──────────────────────────────────────────────────────

class SearchPreferenceModel(Base):
    __tablename__ = "search_preferences"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    filters = Column(JSON, default=dict)
    saved_searches = Column(JSON, default=list)
    alerts_enabled = Column(Boolean, default=True)
    notify_via = Column(JSON, default=list)
    frequency = Column(String(20), default="daily")


# ── Events (audit log) ──────────────────────────────────────────────────────

class EventModel(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    event_type = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), default="")
    entity_id = Column(String(128), default="")
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
