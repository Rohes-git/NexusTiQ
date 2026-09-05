"""Contradiction detection rules.

Identifies inconsistencies across claim documents — e.g. mismatched dates,
conflicting damage descriptions, or discrepancies between the FIR and claim form.
NOT implemented in Milestone 1.
"""

from src.models import ClaimFacts, Document


def detect_contradictions(facts: ClaimFacts, documents: list[Document]) -> list[str]:
    """Find contradictions across the submitted documents.

    Raises:
        NotImplementedError: Always, until Milestone 6.
    """
    raise NotImplementedError(
        "Contradiction detection will be implemented in Milestone 6."
    )
