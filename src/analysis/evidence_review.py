"""Evidence Review Orchestrator (Milestone 6).

Coordinates deterministic cross-document contradiction detection and evidence completeness
verification across claim documents.
Adheres strictly to the architectural boundary:
- Never outputs final claim decisions (APPROVE, REJECT, DENY, FRAUD).
- Surfaces auditable evidence contradictions, missing required documents, and consistent fields.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from src.models import ExtractedFact
from src.analysis.contradiction_detector import (
    ContradictionDetector,
    ContradictionFinding,
    ConsistentFieldFinding,
)
from src.analysis.completeness_checker import (
    CompletenessChecker,
    CompletenessFinding,
    CompletenessStatus,
    determine_claim_type,
)

logger = logging.getLogger("claimlens.analysis")


class EvidenceReviewSummary(BaseModel):
    """Aggregate metrics for evidence consistency and completeness review."""
    contradiction_count: int = Field(0, description="Total number of detected contradictions")
    high_severity_count: int = Field(0, description="Number of high-severity contradictions")
    medium_severity_count: int = Field(0, description="Number of medium-severity contradictions")
    low_severity_count: int = Field(0, description="Number of low-severity contradictions")
    missing_evidence_count: int = Field(0, description="Number of missing required documents/evidence")
    incomplete_evidence_count: int = Field(0, description="Number of incomplete requirements")
    consistent_field_count: int = Field(0, description="Number of verified matching fields across documents")
    total_requirements_checked: int = Field(0, description="Total completeness requirements checked")

    @property
    def total_contradictions(self) -> int:
        return self.contradiction_count

    @property
    def missing_documents_count(self) -> int:
        return self.missing_evidence_count

    @property
    def present_documents_count(self) -> int:
        return max(0, self.total_requirements_checked - self.missing_evidence_count - self.incomplete_evidence_count)

    @property
    def total_required_documents(self) -> int:
        return self.total_requirements_checked

    def __getitem__(self, item: str) -> Any:
        if item == "total_contradictions":
            return self.contradiction_count
        if item == "missing_documents_count":
            return self.missing_evidence_count
        if item == "present_documents_count":
            return self.present_documents_count
        if item == "total_required_documents":
            return self.total_requirements_checked
        return getattr(self, item)


class EvidenceReviewResult(BaseModel):
    """Structured result of deterministic evidence analysis."""
    claim_id: Optional[str] = Field(None, description="Claim reference identifier")
    claim_type: str = Field("UNKNOWN", description="Determined claim type (ACCIDENT / THEFT / UNKNOWN)")
    contradictions: list[ContradictionFinding] = Field(default_factory=list, description="Detected cross-document contradictions")
    completeness: list[CompletenessFinding] = Field(default_factory=list, description="Document completeness findings")
    consistent_fields: list[ConsistentFieldFinding] = Field(default_factory=list, description="Verified consistent fields")
    summary: EvidenceReviewSummary = Field(default_factory=EvidenceReviewSummary, description="Summary counts")


class EvidenceReviewEngine:
    """Orchestrator for deterministic contradiction detection and evidence completeness checking."""

    def __init__(self):
        self.contradiction_detector = ContradictionDetector()
        self.completeness_checker = CompletenessChecker()

    def analyze(
        self,
        claim_id: Optional[str] = None,
        facts: Union[dict[str, Any], list[ExtractedFact], list[dict[str, Any]], None] = None,
        documents: Optional[list[Any]] = None,
        required_evidence_context: Optional[dict[str, Any]] = None,
    ) -> EvidenceReviewResult:
        """Run deterministic evidence analysis on claim facts and document inventory.

        Args:
            claim_id: Optional claim identifier.
            facts: Extracted facts in structured, list, or per-document dictionary format.
            documents: List of document filenames, Document objects, or document summaries.
            required_evidence_context: Optional additional evidence requirements context.

        Returns:
            EvidenceReviewResult containing contradictions, completeness findings, and summary.
        """
        # Determine claim type
        claim_type = determine_claim_type(facts, documents)

        # 1. Contradiction Detection
        contradictions, consistent_fields = self.contradiction_detector.detect(facts, documents)

        # 2. Completeness Checking
        completeness_findings = self.completeness_checker.check(facts, documents)

        # 3. Compute Summary Metrics
        high_sev = sum(1 for c in contradictions if c.severity == "HIGH")
        med_sev = sum(1 for c in contradictions if c.severity == "MEDIUM")
        low_sev = sum(1 for c in contradictions if c.severity == "LOW")
        missing_cnt = sum(1 for f in completeness_findings if f.status == CompletenessStatus.MISSING)
        incomplete_cnt = sum(1 for f in completeness_findings if f.status == CompletenessStatus.INCOMPLETE)

        summary = EvidenceReviewSummary(
            contradiction_count=len(contradictions),
            high_severity_count=high_sev,
            medium_severity_count=med_sev,
            low_severity_count=low_sev,
            missing_evidence_count=missing_cnt,
            incomplete_evidence_count=incomplete_cnt,
            consistent_field_count=len(consistent_fields),
            total_requirements_checked=len(completeness_findings),
        )

        return EvidenceReviewResult(
            claim_id=claim_id,
            claim_type=claim_type,
            contradictions=contradictions,
            completeness=completeness_findings,
            consistent_fields=consistent_fields,
            summary=summary,
        )
