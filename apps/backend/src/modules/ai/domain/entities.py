"""AI domain entities."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Optional
from uuid import UUID, uuid4


@dataclass
class LLMProviderConfig:
    """User-configured LLM provider settings."""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    provider_name: str = "openai"  # openai, anthropic, google, ollama, nvidia_nim, openrouter
    api_key_encrypted: str = ""
    base_url: str = ""
    model: str = "gpt-4o"
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class AIAnalysis:
    """Result of an AI analysis (resume, job matching, etc.)."""
    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    analyzable_type: str = ""  # resume, job, application
    analyzable_id: str = ""
    analysis_type: str = ""  # ats_score, matching, cover_letter, summary
    result: dict = field(default_factory=dict)
    score: Optional[float] = None
    tokens_used: int = 0
    model_used: str = ""
    provider_used: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
