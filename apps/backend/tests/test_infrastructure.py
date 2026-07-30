"""Tests for infrastructure — embedding service, notification providers."""
from __future__ import annotations

import pytest
import numpy as np

from modules.search.infrastructure import EmbeddingService, cosine_similarity


@pytest.mark.asyncio
async def test_embedding_fallback_returns_vector():
    service = EmbeddingService()
    vec = await service.embed_text("Python developer with FastAPI experience")
    assert isinstance(vec, list)
    assert len(vec) == 384  # fallback dim
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.asyncio
async def test_embedding_deterministic():
    service = EmbeddingService()
    vec1 = await service.embed_text("same text")
    vec2 = await service.embed_text("same text")
    assert vec1 == vec2  # fallback is deterministic


@pytest.mark.asyncio
async def test_embedding_different_texts_different():
    service = EmbeddingService()
    vec1 = await service.embed_text("python backend")
    vec2 = await service.embed_text("frontend react")
    assert vec1 != vec2


@pytest.mark.asyncio
async def test_cosine_similarity_identical():
    vec = [1.0, 0.0, 0.0]
    sim = await cosine_similarity(vec, vec)
    assert sim == pytest.approx(1.0, abs=1e-6)


@pytest.mark.asyncio
async def test_cosine_similarity_orthogonal():
    vec_a = [1.0, 0.0, 0.0]
    vec_b = [0.0, 1.0, 0.0]
    sim = await cosine_similarity(vec_a, vec_b)
    assert sim == pytest.approx(0.0, abs=1e-6)


@pytest.mark.asyncio
async def test_cosine_similarity_zero_vector():
    sim = await cosine_similarity([0.0, 0.0], [1.0, 0.0])
    assert sim == 0.0


def test_embedding_batch():
    """Synchronous test for batch embedding."""
    import asyncio
    service = EmbeddingService()
    texts = ["python", "react", "docker"]
    vecs = asyncio.run(service.embed_batch(texts))
    assert len(vecs) == 3
    assert all(len(v) == 384 for v in vecs)
