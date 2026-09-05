"""Policy retriever orchestration for ClaimLens.

Coordinates clause loading, embedding generation/caching, semantic query
construction, vector similarity search, and clause grounding.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional, Union

from src.config import settings
from src.models import ExtractedFact, ClaimFacts
from src.retrieval.policy_loader import PolicyClause, PolicyClauseLoader
from src.retrieval.embedding_service import (
    EmbeddingService,
    EmbeddingServiceError,
    GeminiNotConfiguredError,
)
from src.retrieval.vector_index import (
    VectorIndex,
    RetrievedClause,
    InvalidCacheError,
)
from src.retrieval.query_builder import QueryBuilder
from src.retrieval.grounding import GroundedClause, GroundingService

logger = logging.getLogger("claimlens.retrieval")

DEFAULT_CACHE_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "policy" / "policy_embeddings.json"


class PolicyRetrieverError(Exception):
    """Base exception for policy retriever errors."""
    def __init__(self, message: str, code: str = "RETRIEVAL_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class PolicyRetriever:
    """Retrieves and grounds policy clauses relevant to claim facts."""

    def __init__(
        self,
        loader: Optional[PolicyClauseLoader] = None,
        embedder: Optional[Any] = None,
        cache_path: Optional[Path | str] = None,
    ):
        self.loader = loader or PolicyClauseLoader()
        self.embedder = embedder or EmbeddingService()
        self.cache_path = Path(cache_path) if cache_path else DEFAULT_CACHE_PATH
        self.index = VectorIndex()

    def ensure_index(self) -> VectorIndex:
        """Ensure vector index is loaded or built with current policy embeddings.

        Returns:
            Built and validated VectorIndex instance.

        Raises:
            PolicyRetrieverError: If loading or building fails.
        """
        clauses = self.loader.load_clauses()
        policy_hash = self.loader.compute_policy_hash()
        embedding_model = getattr(self.embedder, "model", "mock-model")

        # 1. Try loading from cache
        if self.cache_path.exists():
            try:
                self.index.load(self.cache_path)
                if self.index.is_valid_for(policy_hash, embedding_model):
                    logger.info("Loaded valid policy embeddings from cache.")
                    return self.index
                else:
                    logger.warning("Cache is stale (policy hash or model mismatch). Rebuilding...")
            except InvalidCacheError as e:
                logger.warning(f"Cache invalid ({e}). Rebuilding...")

        # 2. Build embeddings using embedder
        logger.info(f"Generating policy embeddings using {embedding_model}...")
        texts_to_embed = [
            f"{c.section}\n{c.title}\n{c.text}\nTags: {', '.join(c.tags)}"
            for c in clauses
        ]

        try:
            embeddings = self.embedder.embed_texts(texts_to_embed)
        except GeminiNotConfiguredError as e:
            raise PolicyRetrieverError(
                f"Cannot build policy embeddings: {e.message}. "
                "Run 'python scripts/build_policy_embeddings.py' with GEMINI_API_KEY.",
                code="GEMINI_NOT_CONFIGURED",
            ) from e
        except EmbeddingServiceError as e:
            raise PolicyRetrieverError(
                f"Embedding generation failed: {e.message}",
                code=e.code,
            ) from e

        # 3. Build in-memory index & save cache
        self.index.build(clauses, embeddings, policy_hash, embedding_model)
        try:
            self.index.save(self.cache_path)
            logger.info(f"Saved policy embeddings cache to {self.cache_path}")
        except Exception as e:
            logger.warning(f"Could not write cache file: {e}")

        return self.index

    def retrieve_relevant_clauses(
        self,
        facts: Union[list[ExtractedFact], dict[str, Any], ClaimFacts, None],
        top_k: int = 5,
    ) -> tuple[str, list[GroundedClause]]:
        """Retrieve and ground the most relevant policy clauses for extracted claim facts.

        Args:
            facts: Extracted facts from documents.
            top_k: Number of relevant clauses to retrieve (default 5).

        Returns:
            Tuple of (search query, list of GroundedClause sorted by similarity).

        Raises:
            PolicyRetrieverError: If retrieval fails.
        """
        # Ensure index is ready
        self.ensure_index()

        # Build semantic query
        query = QueryBuilder.build_query(facts)
        if not query.strip():
            raise PolicyRetrieverError("Generated query was empty.", code="EMPTY_QUERY")

        # Generate query embedding
        try:
            query_embedding = self.embedder.embed_text(query)
        except GeminiNotConfiguredError as e:
            raise PolicyRetrieverError(
                f"Cannot embed query: {e.message}",
                code="GEMINI_NOT_CONFIGURED",
            ) from e
        except EmbeddingServiceError as e:
            raise PolicyRetrieverError(
                f"Query embedding failed: {e.message}",
                code=e.code,
            ) from e

        # Vector search
        retrieved = self.index.search(query_embedding, top_k=top_k)

        # Grounding with factual explanations
        grounded = GroundingService.ground_results(retrieved)

        return query, grounded

    def retrieve_clauses(self, facts: ClaimFacts) -> list[PolicyClause]:
        """Backward-compatible method returning matching PolicyClause list."""
        _, grounded = self.retrieve_relevant_clauses(facts, top_k=5)
        clauses_by_id = {c.clause_id: c for c in self.loader.load_clauses()}
        return [clauses_by_id[g.clause_id] for g in grounded if g.clause_id in clauses_by_id]
