"""Embedding generation using LLM provider (text to vector)."""
from __future__ import annotations

import hashlib

import numpy as np

from core.logger import get_logger

logger = get_logger(__name__)

EMBEDDING_DIM = 384


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

    def _fallback_embed(self, text: str, dim: int = EMBEDDING_DIM) -> list[float]:
        """Deterministic hash-seeded embedding (development fallback).

        The hash digest seeds a PRNG instead of being reinterpreted as float32
        bytes: raw digest bytes decode to values spanning the whole float range
        (including inf/NaN), which overflows every downstream norm and dot
        product.
        """
        digest = hashlib.sha256(text.encode()).digest()
        seed = int.from_bytes(digest, "big") % (2**32)
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(dim)
        vec = vec / (np.linalg.norm(vec) + 1e-10)
        return [float(v) for v in vec]


async def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two vectors.

    Returns 0.0 when the vectors have different lengths or either is a
    zero vector, so callers never receive NaN.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.asarray(vec_a, dtype=np.float64)
    b = np.asarray(vec_b, dtype=np.float64)
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if not np.isfinite(norm) or norm == 0:
        return 0.0
    similarity = float(np.dot(a, b) / norm)
    return similarity if np.isfinite(similarity) else 0.0
