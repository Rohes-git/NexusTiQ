"""Embedding service entry point for backward compatibility."""

from src.retrieval.embedding_service import (
    EmbeddingService,
    MockEmbeddingService,
    EmbeddingServiceError,
    GeminiNotConfiguredError,
    GeminiEmbeddingAPIError,
)

__all__ = [
    "EmbeddingService",
    "MockEmbeddingService",
    "EmbeddingServiceError",
    "GeminiNotConfiguredError",
    "GeminiEmbeddingAPIError",
]
