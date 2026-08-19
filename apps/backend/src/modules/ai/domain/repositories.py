"""AI domain repository interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod

from modules.ai.domain.entities import AIAnalysis, LLMProviderConfig


class LLMProviderConfigRepository(ABC):
    @abstractmethod
    async def get_active(self, user_id: str) -> LLMProviderConfig | None: ...

    @abstractmethod
    async def get_by_provider(self, user_id: str, provider_name: str) -> LLMProviderConfig | None: ...

    @abstractmethod
    async def create(self, config: LLMProviderConfig) -> LLMProviderConfig: ...

    @abstractmethod
    async def update(self, config: LLMProviderConfig) -> LLMProviderConfig: ...

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[LLMProviderConfig]: ...


class AIAnalysisRepository(ABC):
    @abstractmethod
    async def get_by_id(self, analysis_id: str) -> AIAnalysis | None: ...

    @abstractmethod
    async def get_for_user(self, user_id: str) -> list[AIAnalysis]: ...

    @abstractmethod
    async def get_for_analyzable(self, analyzable_type: str, analyzable_id: str) -> list[AIAnalysis]: ...

    @abstractmethod
    async def create(self, analysis: AIAnalysis) -> AIAnalysis: ...

    @abstractmethod
    async def update(self, analysis: AIAnalysis) -> AIAnalysis: ...
