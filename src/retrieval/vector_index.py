"""Lightweight NumPy-based vector index for policy clause retrieval.

Stores clause embeddings and metadata locally, computes cosine similarity,
and produces deterministic ranked retrieval results without requiring an
external vector database.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import numpy as np
from pydantic import BaseModel, Field

from src.retrieval.policy_loader import PolicyClause


class RetrievedClause(BaseModel):
    """A policy clause retrieved by vector search with its similarity score."""
    clause_id: str = Field(..., description="Clause identifier e.g. '2.1'")
    section: str = Field(..., description="Section title")
    title: str = Field(..., description="Clause title")
    text: str = Field(..., description="Exact policy clause text")
    similarity_score: float = Field(..., ge=-1.0, le=1.0, description="Cosine similarity score")


class VectorIndexError(Exception):
    """Base exception for vector index operations."""
    pass


class EmptyIndexError(VectorIndexError):
    """Raised when querying an unbuilt or empty index."""
    pass


class DimensionMismatchError(VectorIndexError):
    """Raised when query vector dimension does not match index dimension."""
    pass


class InvalidCacheError(VectorIndexError):
    """Raised when the cache file is invalid or corrupt."""
    pass


class VectorIndex:
    """NumPy-based in-memory vector index with local persistence."""

    def __init__(self):
        self.policy_hash: str = ""
        self.embedding_model: str = ""
        self.clauses: list[PolicyClause] = []
        self._embeddings: Optional[np.ndarray] = None  # shape (N, D)

    @property
    def is_built(self) -> bool:
        return (
            self._embeddings is not None
            and len(self.clauses) > 0
            and self._embeddings.shape[0] == len(self.clauses)
        )

    @property
    def dimension(self) -> int:
        if self._embeddings is None or self._embeddings.size == 0:
            return 0
        return self._embeddings.shape[1]

    def build(
        self,
        clauses: list[PolicyClause],
        embeddings: list[list[float]],
        policy_hash: str,
        embedding_model: str,
    ) -> None:
        """Build the index from clauses and corresponding embeddings.

        Args:
            clauses: List of PolicyClause instances.
            embeddings: Parallel list of embedding vectors.
            policy_hash: SHA-256 hash of the policy source.
            embedding_model: Model name used to generate embeddings.

        Raises:
            VectorIndexError: If counts mismatch or empty data.
        """
        if not clauses:
            raise VectorIndexError("Cannot build index with zero clauses.")
        if len(clauses) != len(embeddings):
            raise VectorIndexError(
                f"Mismatch: {len(clauses)} clauses but {len(embeddings)} embeddings provided."
            )

        emb_array = np.array(embeddings, dtype=np.float32)
        if emb_array.ndim != 2 or emb_array.shape[0] != len(clauses):
            raise VectorIndexError(f"Invalid embeddings matrix shape: {emb_array.shape}")

        self.clauses = list(clauses)
        self._embeddings = emb_array
        self.policy_hash = policy_hash
        self.embedding_model = embedding_model

    def search(self, query_embedding: list[float], top_k: int = 5) -> list[RetrievedClause]:
        """Search the index for the most relevant clauses via cosine similarity.

        Args:
            query_embedding: Dense embedding vector for query.
            top_k: Number of top results to return.

        Returns:
            List of RetrievedClause sorted by similarity score (highest first).

        Raises:
            EmptyIndexError: If index has not been built.
            DimensionMismatchError: If query vector dimension mismatches index.
        """
        if not self.is_built or self._embeddings is None:
            raise EmptyIndexError("Vector index is empty or has not been built.")

        q_vec = np.array(query_embedding, dtype=np.float32)
        if q_vec.ndim == 1:
            q_vec = q_vec.reshape(1, -1)

        if q_vec.shape[1] != self.dimension:
            raise DimensionMismatchError(
                f"Query vector dimension ({q_vec.shape[1]}) does not match index dimension ({self.dimension})."
            )

        # Cosine similarity: (A . B) / (||A|| * ||B||)
        # Compute norms
        doc_norms = np.linalg.norm(self._embeddings, axis=1, keepdims=True)  # (N, 1)
        q_norm = np.linalg.norm(q_vec, axis=1, keepdims=True)  # (1, 1)

        # Avoid division by zero
        doc_norms = np.where(doc_norms == 0, 1e-10, doc_norms)
        q_norm = np.where(q_norm == 0, 1e-10, q_norm)

        normalized_docs = self._embeddings / doc_norms
        normalized_q = q_vec / q_norm

        similarities = np.dot(normalized_docs, normalized_q.T).flatten()  # (N,)

        # Build list of (score, clause) for deterministic sorting
        scored_clauses: list[tuple[float, PolicyClause]] = []
        for idx, clause in enumerate(self.clauses):
            score = float(similarities[idx])
            # Clamp to [-1.0, 1.0] to guard against float precision artifacts
            score = max(-1.0, min(1.0, score))
            scored_clauses.append((score, clause))

        # Deterministic sort: similarity descending, then clause_id ascending
        scored_clauses.sort(key=lambda item: (-item[0], item[1].clause_id))

        results: list[RetrievedClause] = []
        for score, clause in scored_clauses[:top_k]:
            results.append(RetrievedClause(
                clause_id=clause.clause_id,
                section=clause.section,
                title=clause.title,
                text=clause.text,
                similarity_score=round(score, 4),
            ))

        return results

    def save(self, path: Path | str) -> None:
        """Save index metadata and embeddings to a local JSON file."""
        if not self.is_built or self._embeddings is None:
            raise EmptyIndexError("Cannot save an unbuilt vector index.")

        target_path = Path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "policy_hash": self.policy_hash,
            "embedding_model": self.embedding_model,
            "dimension": self.dimension,
            "clause_count": len(self.clauses),
            "clauses": [c.model_dump() for c in self.clauses],
            "embeddings": self._embeddings.tolist(),
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load(self, path: Path | str) -> None:
        """Load index from a saved JSON cache file.

        Raises:
            InvalidCacheError: If file is missing, invalid, or corrupt.
        """
        cache_path = Path(path)
        if not cache_path.exists():
            raise InvalidCacheError(f"Cache file not found at: {cache_path}")

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise InvalidCacheError(f"Failed to read cache file: {e}") from e

        if not isinstance(data, dict):
            raise InvalidCacheError("Cache payload must be a JSON object.")

        required_keys = ["policy_hash", "embedding_model", "clauses", "embeddings"]
        for k in required_keys:
            if k not in data:
                raise InvalidCacheError(f"Missing key '{k}' in cache file.")

        raw_clauses = data["clauses"]
        raw_embeddings = data["embeddings"]

        if len(raw_clauses) != len(raw_embeddings):
            raise InvalidCacheError("Cache clause count does not match embedding count.")

        try:
            clauses = [PolicyClause.model_validate(c) for c in raw_clauses]
            embeddings = np.array(raw_embeddings, dtype=np.float32)
        except Exception as e:
            raise InvalidCacheError(f"Malformed clauses or embeddings in cache: {e}") from e

        self.policy_hash = data.get("policy_hash", "")
        self.embedding_model = data.get("embedding_model", "")
        self.clauses = clauses
        self._embeddings = embeddings

    def is_valid_for(self, policy_hash: str, embedding_model: str) -> bool:
        """Check if currently loaded index matches policy hash and embedding model."""
        return (
            self.is_built
            and self.policy_hash == policy_hash
            and self.embedding_model == embedding_model
        )
