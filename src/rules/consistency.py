"""Contradiction detection rules (Milestone 6).

Identifies inconsistencies across claim documents — e.g. mismatched dates,
conflicting repair amounts, or discrepancies between documents.
"""

from __future__ import annotations

from typing import Any, Optional, Union
from src.models import ClaimFacts, Document, ExtractedFact
from src.analysis.contradiction_detector import ContradictionDetector, ContradictionFinding


def detect_contradictions(
    facts: Union[ClaimFacts, dict[str, Any], list[ExtractedFact], None],
    documents: Optional[list[Union[Document, str, dict[str, Any]]]] = None,
) -> list[str]:
    """Find and summarize contradictions across the submitted documents.

    Args:
        facts: Claim facts object, dictionary, or extracted facts list.
        documents: List of Document objects or filenames.

    Returns:
        List of human-readable contradiction descriptions.
    """
    if isinstance(facts, ClaimFacts):
        facts_dict = facts.model_dump()
    else:
        facts_dict = facts

    detector = ContradictionDetector()
    findings, _ = detector.detect(facts_dict, documents)

    return [f.message for f in findings]


def detect_contradiction_findings(
    facts: Union[ClaimFacts, dict[str, Any], list[ExtractedFact], None],
    documents: Optional[list[Union[Document, str, dict[str, Any]]]] = None,
) -> list[ContradictionFinding]:
    """Find detailed ContradictionFinding objects across submitted documents."""
    if isinstance(facts, ClaimFacts):
        facts_dict = facts.model_dump()
    else:
        facts_dict = facts

    detector = ContradictionDetector()
    findings, _ = detector.detect(facts_dict, documents)
    return findings
