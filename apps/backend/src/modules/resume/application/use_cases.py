"""Resume application use cases — upload, parse, list."""
from __future__ import annotations

from core.exceptions import NotFoundError, ValidationError
from core.logger import get_logger
from modules.resume.infrastructure.repositories import ResumeRepository

logger = get_logger(__name__)


class UploadResumeUseCase:
    def __init__(self, repo: ResumeRepository):
        self._repo = repo

    async def execute(self, user_id: str, title: str, file_content: bytes, filename: str):
        content_text = self._extract_pdf_text(file_content)
        if not content_text:
            # A scanned PDF has no text layer. Say so rather than storing an
            # empty resume that silently scores 0 on every analysis.
            raise ValidationError(
                "Não foi possível extrair texto deste PDF. "
                "Se ele for digitalizado, envie uma versão com texto selecionável."
            )

        resume = await self._repo.create(
            user_id=user_id,
            title=title,
            content_text=content_text,
            file_url=f"uploads/{filename}",
        )
        logger.info("resume_uploaded", user_id=user_id, title=title, chars=len(content_text))
        return resume

    def _extract_pdf_text(self, content: bytes) -> str:
        try:
            import io

            from pypdf import PdfReader
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

    async def execute(self, resume_id: str):
        resume = await self._repo.get_by_id(resume_id)
        if not resume:
            raise NotFoundError("Resume not found")
        return resume


class ListResumesUseCase:
    def __init__(self, repo: ResumeRepository):
        self._repo = repo

    async def execute(self, user_id: str) -> list:
        return await self._repo.list_by_user(user_id)
