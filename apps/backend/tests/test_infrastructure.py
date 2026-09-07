"""Tests for the embedding service backing semantic search."""
from __future__ import annotations

import pytest

from modules.search.infrastructure import (
    EMBEDDING_DIM,
    EmbeddingService,
    cosine_similarity,
    rank_by_similarity,
)


@pytest.mark.asyncio
async def test_local_embedding_has_fixed_dimension():
    vector = await EmbeddingService().embed_text("Python developer with FastAPI experience")
    assert len(vector) == EMBEDDING_DIM
    assert all(isinstance(v, float) for v in vector)


@pytest.mark.asyncio
async def test_local_embedding_is_deterministic():
    service = EmbeddingService()
    assert await service.embed_text("same text") == await service.embed_text("same text")


@pytest.mark.asyncio
async def test_local_embedding_distinguishes_texts():
    service = EmbeddingService()
    assert await service.embed_text("python backend") != await service.embed_text("frontend react")


def test_local_embedding_is_unit_length():
    vector = EmbeddingService().local_embed("docker kubernetes terraform")
    assert cosine_similarity(vector, vector) == pytest.approx(1.0, abs=1e-9)


def test_local_embedding_of_empty_text_is_zero_vector():
    assert EmbeddingService().local_embed("") == [0.0] * EMBEDDING_DIM


def test_related_documents_score_above_unrelated_ones():
    """The point of the vectorizer: shared vocabulary must mean higher similarity.

    The previous implementation seeded a PRNG from a hash of the whole
    document, so this relationship did not hold and search returned noise.
    """
    service = EmbeddingService()
    backend = service.local_embed("senior backend engineer python django postgres")
    similar = service.local_embed("backend developer python django postgresql docker")
    unrelated = service.local_embed("graphic designer photoshop illustrator branding")

    assert cosine_similarity(backend, similar) > cosine_similarity(backend, unrelated)
    assert cosine_similarity(backend, similar) > 0.3


def test_cosine_similarity_identical():
    vector = [1.0, 0.0, 0.0]
    assert cosine_similarity(vector, vector) == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_orthogonal():
    assert cosine_similarity([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]) == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_zero_vector():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0


def test_cosine_similarity_mismatched_lengths():
    """Stored vectors can predate a model switch; comparing them must not crash."""
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0


@pytest.mark.asyncio
async def test_embed_batch_returns_one_vector_per_input():
    vectors = await EmbeddingService().embed_batch(["python", "react", "docker"])
    assert len(vectors) == 3
    assert all(len(v) == EMBEDDING_DIM for v in vectors)


@pytest.mark.asyncio
async def test_embed_batch_of_nothing_is_empty():
    assert await EmbeddingService().embed_batch([]) == []


def test_rank_by_similarity_orders_best_first_and_respects_limit():
    service = EmbeddingService()
    query = service.local_embed("python backend developer")
    candidates = [
        ("match", service.local_embed("python backend developer django")),
        ("weak", service.local_embed("marketing manager brand strategy")),
        ("mid", service.local_embed("python data analyst")),
    ]

    ranked = rank_by_similarity(query, candidates, limit=2)
    assert [key for key, _ in ranked] == ["match", "mid"]


def test_rank_by_similarity_skips_wrong_dimension_vectors():
    query = [1.0, 0.0, 0.0]
    ranked = rank_by_similarity(query, [("bad", [1.0, 0.0]), ("good", [1.0, 0.0, 0.0])], limit=5)
    assert [key for key, _ in ranked] == ["good"]
