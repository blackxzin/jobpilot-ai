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

    async def execute(self, user_id: str, job_id: str, resume_text: str, job: dict) -> dict:
        content = await self._llm.generate_cover_letter(resume_text, job)
        saved = await self._repo.create(
            user_id=user_id,
            job_id=job_id,
            content=content,
        )
        logger.info("cover_letter_generated", user_id=user_id, job_id=job_id)
        return saved
