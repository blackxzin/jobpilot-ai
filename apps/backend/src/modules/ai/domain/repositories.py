"""AI domain repository interfaces."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from modules.ai.domain.entities import LLMProviderConfig, AIAnalysis


class LLMProviderConfigRepository(ABC):
    @abstractmethod
    async def get_active(self, user_id: str) -> Optional[LLMProviderConfig]: ...

    @abstractmethod
    async def get_by_provider(self, user_id: str, provider_name: str) -> Optional[LLMProviderConfig]: ...

    @abstractmethod
    async def create(self, config: LLMProviderConfig) -> LLMProviderConfig: ...

    @abstractmethod
    async def update(self, config: LLMProviderConfig) -> LLMProviderConfig: ...

    @abstractmethod
    async def list_for_user(self, user_id: str) -> list[LLMProviderConfig]: ...


class AIAnalysisRepository(ABC):
    @abstractmethod
    async def get_by_id(self, analysis_id: str) -> Optional[AIAnalysis]: ...

    @abstractmethod
    async def get_for_user(self, user_id: str) -> list[AIAnalysis]: ...

    @abstractmethod
    async def get_for_analyzable(self, analyzable_type: str, analyzable_id: str) -> list[AIAnalysis]: ...

    @abstractmethod
    async def create(self, analysis: AIAnalysis) -> AIAnalysis: ...

    @abstractmethod
    async def update(self, analysis: AIAnalysis) -> AIAnalysis: ...
