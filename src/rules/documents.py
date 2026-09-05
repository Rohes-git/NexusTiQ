"""Document completeness rules.

Checks whether the required documents have been submitted and are legible.
NOT implemented in Milestone 1.
"""

from src.models import Document, Finding


def check_document_completeness(documents: list[Document]) -> list[Finding]:
    """Verify all required claim documents are present and readable.

    Raises:
        NotImplementedError: Always, until Milestone 5.
    """
    raise NotImplementedError(
        "Document completeness checks will be implemented in Milestone 5."
    )
