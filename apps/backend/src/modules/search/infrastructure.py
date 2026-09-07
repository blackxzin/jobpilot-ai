"""Embedding generation for semantic job search.

Two strategies, in priority order:

1. An OpenAI-compatible embeddings API when a key is configured.
2. A local hashed bag-of-words vectorizer, used offline.

The local strategy replaces an earlier one that seeded a PRNG from a hash of
the whole document. That produced a valid-looking unit vector whose direction
was unrelated to the text, so two near-identical job posts scored no closer
than two unrelated ones — the feature returned ranked noise. Hashing individual
tokens into buckets keeps documents that share vocabulary genuinely close.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata

import numpy as np

from core.logger import get_logger

logger = get_logger(__name__)

# Dimension of the local vectorizer. Must stay fixed: vectors of different
# lengths cannot be compared, and stored embeddings are not re-generated.
EMBEDDING_DIM = 384

# Cap on text sent to a remote embeddings API, which charges by token.
_MAX_INPUT_CHARS = 8000

# Internal punctuation matters ("next.js", "c++"); trailing punctuation is
# sentence structure and must not become part of the term.
_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+#._-]*")
_TRAILING_PUNCTUATION = "._-"


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _tokens(text: str) -> list[str]:
    tokens = (t.rstrip(_TRAILING_PUNCTUATION) for t in _TOKEN_RE.findall(_normalize(text)))
    return [t for t in tokens if t][:4000]


def _bucket(token: str, dim: int) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % dim


class EmbeddingService:
    """Turn text into a comparable vector, with or without a network."""

    def __init__(self, api_key: str = "", model: str = "text-embedding-3-small"):
        self._api_key = api_key
        self._model = model
        self._client = None

    @property
    def is_remote(self) -> bool:
        """True when a real embeddings API will be used."""
        return bool(self._api_key)

    async def _get_client(self):
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def embed_text(self, text: str) -> list[float]:
        """Return an embedding for `text`.

        Falls back to the local vectorizer when no key is set or the API call
        fails, so search degrades in quality rather than breaking.
        """
        if not self._api_key:
            return self.local_embed(text)
        try:
            client = await self._get_client()
            response = await client.embeddings.create(
                model=self._model, input=(text or "")[:_MAX_INPUT_CHARS]
            )
            return list(response.data[0].embedding)
        except Exception as e:
            logger.warning("embedding_api_failed_using_local", error=str(e))
            return self.local_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed several documents.

        The remote path sends one batched request; the API bills and rate-limits
        per request, so looping one call per document is both slower and dearer.
        """
        if not texts:
            return []
        if not self._api_key:
            return [self.local_embed(t) for t in texts]
        try:
            client = await self._get_client()
            response = await client.embeddings.create(
                model=self._model, input=[(t or "")[:_MAX_INPUT_CHARS] for t in texts]
            )
            ordered = sorted(response.data, key=lambda d: d.index)
            return [list(item.embedding) for item in ordered]
        except Exception as e:
            logger.warning("embedding_batch_failed_using_local", error=str(e))
            return [self.local_embed(t) for t in texts]

    def local_embed(self, text: str, dim: int = EMBEDDING_DIM) -> list[float]:
        """Hashed bag-of-words vector, L2-normalized.

        Each token is hashed into one of `dim` buckets and contributes
        `1 + log(count)`. Documents sharing vocabulary land in the same
        buckets, which is what makes the similarity meaningful.
        """
        counts: dict[int, float] = {}
        for token in _tokens(text):
            index = _bucket(token, dim)
            counts[index] = counts.get(index, 0.0) + 1.0

        # Sub-linear damping, as in TF-IDF: a term repeated 20 times matters
        # more than one used once, but not twenty times more.
        vector = np.zeros(dim, dtype=np.float64)
        for index, count in counts.items():
            vector[index] = 1.0 + math.log(count)

        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            return [0.0] * dim
        return [float(v) for v in vector / norm]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Cosine similarity of two vectors, clamped to [-1, 1].

    Returns 0.0 for mismatched lengths or zero vectors so callers never see
    NaN — mismatched lengths happen when stored vectors predate a switch
    between the local and remote embedding models.
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.asarray(vec_a, dtype=np.float64)
    b = np.asarray(vec_b, dtype=np.float64)
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    if not np.isfinite(norm) or norm == 0.0:
        return 0.0
    similarity = float(np.dot(a, b) / norm)
    if not np.isfinite(similarity):
        return 0.0
    return max(-1.0, min(1.0, similarity))


def rank_by_similarity(
    query_vector: list[float], candidates: list[tuple[str, list[float]]], limit: int
) -> list[tuple[str, float]]:
    """Return the `limit` best (key, score) pairs, scored in one vectorized pass.

    Scoring in NumPy rather than a Python loop keeps a few thousand stored jobs
    well under a millisecond.
    """
    usable = [(key, vec) for key, vec in candidates if vec and len(vec) == len(query_vector)]
    if not usable or not query_vector:
        return []

    matrix = np.asarray([vec for _, vec in usable], dtype=np.float64)
    query = np.asarray(query_vector, dtype=np.float64)

    norms = np.linalg.norm(matrix, axis=1) * float(np.linalg.norm(query))
    with np.errstate(divide="ignore", invalid="ignore"):
        scores = np.where(norms > 0, matrix @ query / norms, 0.0)
    scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)

    top = np.argsort(-scores)[:limit]
    return [(usable[i][0], float(scores[i])) for i in top]
