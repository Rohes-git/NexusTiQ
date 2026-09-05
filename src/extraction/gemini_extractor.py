"""Gemini-based document extraction.

Will use Gemini to extract structured claim facts from uploaded PDFs.
NOT implemented in Milestone 1 — no API calls are made.
"""

from src.models import ClaimFacts, Document


class GeminiExtractor:
    """Extracts structured facts from claim documents using Gemini."""

    def extract_claim_facts(self, document: Document) -> ClaimFacts:
        """Extract structured claim facts from a document.

        Args:
            document: The claim document to process.

        Returns:
            Extracted facts — placeholder in Milestone 1.

        Raises:
            NotImplementedError: Always, until Gemini integration in Milestone 3.
        """
        raise NotImplementedError(
            "Document extraction requires Gemini integration (Milestone 3)."
        )

    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract raw text from a PDF.

        Raises:
            NotImplementedError: Always, until Milestone 3.
        """
        raise NotImplementedError(
            "PDF text extraction will be implemented in Milestone 3."
        )
