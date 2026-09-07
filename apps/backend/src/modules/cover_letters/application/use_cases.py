"""Cover letters application use cases."""
from __future__ import annotations

from core.logger import get_logger
from modules.ai.application.llm_service import LLMService
from modules.cover_letters.infrastructure.repositories import CoverLetterRepository

logger = get_logger(__name__)


class GenerateCoverLetterUseCase:
    def __init__(self, llm_service: LLMService, repo: CoverLetterRepository):
        self._llm = llm_service
        self._repo = repo

    async def execute(
        self,
        user_id: str,
        job_id: str,
        resume_text: str,
        job: dict,
        language: str = "pt-BR",
        tone: str = "professional",
    ) -> dict:
        content = await self._llm.generate_cover_letter(resume_text, job, language=language, tone=tone)
        title = f"{job.get('title', '')} - {job.get('company', '')}".strip(" -")
        saved = await self._repo.create(
            user_id=user_id,
            job_id=job_id,
            content=content,
            title=title,
            language=language,
            tone=tone,
        )
        logger.info("cover_letter_generated", user_id=user_id, job_id=job_id, language=language, tone=tone)
        return saved
