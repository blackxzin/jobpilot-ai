"""Jobs application use cases."""
from __future__ import annotations

from typing import Optional

from core.exceptions import NotFoundError
from modules.jobs.infrastructure.repositories import JobRepository
from modules.users.infrastructure.providers.gupy_client import GupyClient


class SearchJobsUseCase:
    def __init__(self, job_repo: JobRepository):
        self._job_repo = job_repo

    async def execute(self, query: str = "", location: str = "", remote: bool = False, page: int = 1, per_page: int = 20):
        return await self._job_repo.search(query=query, location=location, remote=remote, page=page, per_page=per_page)


class SearchGupyUseCase:
    async def execute(self, query: str = "", location: str = "", remote: bool = False, page: int = 1, per_page: int = 20):
        client = GupyClient()
        try:
            return await client.search_jobs(query=query, location=location, remote=remote, page=page, per_page=per_page)
        finally:
            await client.close()


class GetJobUseCase:
    def __init__(self, job_repo: JobRepository):
        self._job_repo = job_repo

    async def execute(self, job_id: str):
        job = await self._job_repo.get_by_id(job_id)
        if not job:
            raise NotFoundError("Job not found")
        return job
