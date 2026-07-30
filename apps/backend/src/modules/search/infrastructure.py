"""Embedding generation using LLM provider (text to vector)."""
from __future__ import annotations

import json
import hashlib
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """Generate embeddings using configured LLM provider.

    Uses OpenAI-compatible embedding API, falling back to
    a simple hash-based embedding for development/offline use.
    """

    def __init__(self, api_key: str = ""):
        self._api_key = api_key
        self._client = None

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=self._api_key or "sk-placeholder")
        return self._client

    async def embed_text(self, text: str, model: str = "text-embedding-3-small") -> list[float]:
        """Generate embedding vector for text."""
        try:
            client = await self._get_client()
            resp = await client.embeddings.create(model=model, input=text[:8000])
            return resp.data[0].embedding
        except Exception as e:
            logger.warning("embedding_api_failed, using fallback", error=str(e))
            return self._fallback_embed(text)

    async def embed_batch(self, texts: list[str], model: str = "text-embedding-3-small") -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        results = []
        for t in texts:
            vec = await self.embed_text(t, model)
            results.append(vec)
        return results

    def _fallback_embed(self, text: str, dim: int = 384) -> list[float]:
        """Deterministic hash-based embedding (development fallback)."""
        import numpy as np
        from numpy import dot, linalg

        digest = hashlib.sha256(text.encode()).digest()
        rng = np.frombuffer(digest, dtype=np.float32)
        rng = rng[:dim] if len(rng) >= dim else np.pad(rng, (0, dim - len(rng)))
        rng = rng / (linalg.norm(rng) + 1e-10)
        return rng.tolist()


async def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    import numpy as np
    a = np.array(vec_a)
    b = np.array(vec_b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)
