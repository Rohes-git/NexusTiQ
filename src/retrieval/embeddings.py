"""Embedding service for semantic search over policy documents.

Will provide vector embeddings for policy clause retrieval.
NOT implemented in Milestone 1.
"""


class EmbeddingService:
    """Generates embeddings for policy text and claim facts."""

    def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text.

        Raises:
            NotImplementedError: Always, until Milestone 4.
        """
        raise NotImplementedError(
            "Embedding service will be implemented in Milestone 4."
        )

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Raises:
            NotImplementedError: Always, until Milestone 4.
        """
        raise NotImplementedError(
            "Batch embedding will be implemented in Milestone 4."
        )
