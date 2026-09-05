"""Gemini embedding service for policy retrieval and fact queries.

Uses the official google-genai SDK to generate vector embeddings using
configurable Gemini embedding models (e.g., text-embedding-004).
Includes a deterministic MockEmbeddingService for offline testing.
"""

from __future__ import annotations

import hashlib
import logging
import math
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.config import settings

logger = logging.getLogger("claimlens.retrieval")


class EmbeddingServiceError(Exception):
    """Base exception for embedding service errors."""
    def __init__(self, message: str, code: str = "EMBEDDING_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class GeminiNotConfiguredError(EmbeddingServiceError):
    """Raised when GEMINI_API_KEY is not configured."""
    def __init__(self, message: str = "GEMINI_API_KEY is not configured in the environment."):
        super().__init__(message, code="GEMINI_NOT_CONFIGURED")


class GeminiEmbeddingAPIError(EmbeddingServiceError):
    """Raised when Gemini embedding API call fails."""
    def __init__(self, message: str):
        super().__init__(message, code="GEMINI_API_ERROR")


class EmbeddingService:
    """Generates vector embeddings using Gemini's Embedding API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model if model is not None else settings.gemini_embedding_model
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise GeminiNotConfiguredError()
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single string.

        Args:
            text: Input text to embed.

        Returns:
            List of floats representing the embedding vector.

        Raises:
            GeminiNotConfiguredError: If API key is missing.
            GeminiEmbeddingAPIError: If API call fails.
        """
        if not text or not text.strip():
            raise EmbeddingServiceError("Cannot embed empty or whitespace-only text.")

        client = self._get_client()
        try:
            response = client.models.embed_content(
                model=self.model,
                contents=text.strip(),
            )
            if not response.embeddings or not response.embeddings[0].values:
                raise GeminiEmbeddingAPIError("Gemini returned empty embedding values.")
            return list(response.embeddings[0].values)
        except APIError as e:
            raise GeminiEmbeddingAPIError(f"Gemini Embedding API error: {str(e)}") from e
        except EmbeddingServiceError:
            raise
        except Exception as e:
            raise GeminiEmbeddingAPIError(f"Failed to generate embedding: {str(e)}") from e

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of strings.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []

        cleaned_texts = [t.strip() for t in texts if t and t.strip()]
        if len(cleaned_texts) != len(texts):
            raise EmbeddingServiceError("All texts in batch must be non-empty.")

        client = self._get_client()
        try:
            response = client.models.embed_content(
                model=self.model,
                contents=cleaned_texts,
            )
            if not response.embeddings:
                raise GeminiEmbeddingAPIError("Gemini returned empty batch embeddings.")
            return [list(emb.values) for emb in response.embeddings]
        except APIError as e:
            raise GeminiEmbeddingAPIError(f"Gemini Batch Embedding API error: {str(e)}") from e
        except EmbeddingServiceError:
            raise
        except Exception as e:
            raise GeminiEmbeddingAPIError(f"Failed to generate batch embeddings: {str(e)}") from e


class MockEmbeddingService:
    """Deterministic offline embedding generator for testing without Gemini."""

    def __init__(self, dimension: int = 64):
        self.dimension = dimension

    def _generate_vector(self, text: str) -> list[float]:
        """Produce a deterministic normalized dense vector for the text."""
        words = text.lower().split()
        vec = [0.0] * self.dimension
        for word in words:
            # Hash word into dimension slots
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            slot = h % self.dimension
            weight = (h >> 8) % 100 / 100.0 + 0.5
            vec[slot] += weight

        # Normalize to unit length
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [x / norm for x in vec]
        else:
            vec[0] = 1.0
        return vec

    def embed_text(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise EmbeddingServiceError("Cannot embed empty text.")
        return self._generate_vector(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self.embed_text(t) for t in texts]
