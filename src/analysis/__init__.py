"""Analysis package for ClaimLens (Milestone 6).

Provides deterministic contradiction detection, evidence completeness verification,
and cross-document evidence consistency analysis.
"""

from src.analysis.contradiction_detector import (
    ContradictionFinding,
    ContradictionCategory,
    ContradictionSeverity,
    ConsistentFieldFinding,
    ContradictionDetector,
)
from src.analysis.completeness_checker import (
    CompletenessFinding,
    CompletenessStatus,
    CompletenessChecker,
    determine_claim_type,
)
from src.analysis.evidence_review import (
    EvidenceReviewEngine,
    EvidenceReviewResult,
    EvidenceReviewSummary,
)

__all__ = [
    "ContradictionFinding",
    "ContradictionCategory",
    "ContradictionSeverity",
    "ConsistentFieldFinding",
    "ContradictionDetector",
    "CompletenessFinding",
    "CompletenessStatus",
    "CompletenessChecker",
    "determine_claim_type",
    "EvidenceReviewEngine",
    "EvidenceReviewResult",
    "EvidenceReviewSummary",
]
