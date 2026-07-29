"""Resume application use cases — upload, parse, list."""
from __future__ import annotations

from typing import Optional

from core.exceptions import NotFoundError
from modules.resume.infrastructure.repositories import ResumeRepository
from core.logger import get_logger

logger = get_logger(__name__)


class UploadResumeUseCase:
    def __init__(self, repo: ResumeRepository):
        self._repo = repo

    async def execute(self, user_id: str, title: str, file_content: bytes, filename: str) -> dict:
        # Extract text from PDF
        content_text = self._extract_pdf_text(file_content)
        if not content_text:
            content_text = "[Could not extract text from PDF]"

        resume = await self._repo.create(
            user_id=user_id,
            title=title,
            content_text=content_text,
            file_url=f"uploads/{filename}",
        )
        logger.info("resume_uploaded", user_id=user_id, title=title)
        return resume

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
            import io
            reader = PdfReader(io.BytesIO(content))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text.strip()
        except Exception as e:
            logger.warning("pdf_extraction_failed", error=str(e))
            return ""


class GetResumeUseCase:
    def __init__(self, repo: ResumeRepository):
        self._repo = repo

    async def execute(self, resume_id: str) -> Optional[dict]:
        resume = await self._repo.get_by_id(resume_id)
        if not resume:
            raise NotFoundError("Resume not found")
        return resume


class ListResumesUseCase:
    def __init__(self, repo: ResumeRepository):
        self._repo = repo

    async def execute(self, user_id: str) -> list:
        return await self._repo.list_by_user(user_id)
