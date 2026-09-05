"""ClaimLens Review Recommendation Engine (Milestone 7).

Deterministic, auditable recommendation engine that synthesizes:
- Policy rule findings (Milestone 5)
- Cross-document contradictions (Milestone 6)
- Document completeness findings (Milestone 6)

Strict Non-Adjudication Boundary:
- NEVER outputs APPROVE, REJECT, DENY, FRAUD, or final claim adjudication.
- Uses strictly reviewer-oriented statuses:
    • READY_FOR_REVIEW
    • REQUEST_INFORMATION
    • ESCALATE_FOR_HUMAN_REVIEW
- Does not resolve contradictions, decide which document is correct, calculate settlements,
  or perform fraud detection.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, Field, field_validator

from src.rules.policy_rules import PolicyFinding, RuleFindingStatus
from src.analysis.contradiction_detector import ContradictionFinding, ContradictionSeverity
from src.analysis.completeness_checker import CompletenessFinding, CompletenessStatus

logger = logging.getLogger("claimlens.recommendation")


# ── Controlled Review Statuses ────────────────────────────────────────────

class ReviewStatus(str, Enum):
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    REQUEST_INFORMATION = "REQUEST_INFORMATION"
    ESCALATE_FOR_HUMAN_REVIEW = "ESCALATE_FOR_HUMAN_REVIEW"


# Set of strictly prohibited final adjudication terms
PROHIBITED_DECISION_TERMS = frozenset([
    "APPROVE",
    "APPROVED",
    "REJECT",
    "REJECTED",
    "DENY",
    "DENIED",
    "FRAUD",
    "FRAUDULENT",
    "FINAL CLAIM DECISION",
    "SETTLEMENT DECISION",
])


# Standardized reviewer recommended actions
ACTION_REQUEST_INFORMATION = (
    "Obtain clarification or supporting documentation for the identified evidence gaps."
)
ACTION_ESCALATE_FOR_HUMAN_REVIEW = (
    "Review the policy finding and supporting evidence before proceeding."
)
ACTION_READY_FOR_REVIEW = (
    "Evidence package is sufficiently complete and internally consistent for standard human review."
)


# ── Data Models ───────────────────────────────────────────────────────────

class TriggeringFinding(BaseModel):
    """A concise summary of an issue triggering the review recommendation."""
    finding_type: str = Field(..., description="'MISSING_EVIDENCE', 'CONTRADICTION', 'POLICY_FAILURE', or 'POLICY_WARNING'")
    title: str = Field(..., description="Short title of the finding")
    detail: str = Field(..., description="Specific explanation of why this triggered the recommendation")
    source: Optional[str] = Field(None, description="Document, clause ID, or field name citation")
    severity: Optional[str] = Field(None, description="Severity level or status (e.g. HIGH, MISSING, FAIL)")


class ReviewRecommendation(BaseModel):
    """Auditable review recommendation outcome for a human claims investigator."""
    status: ReviewStatus = Field(..., description="READY_FOR_REVIEW | REQUEST_INFORMATION | ESCALATE_FOR_HUMAN_REVIEW")
    reason: str = Field(..., description="Clear explanation for the assigned review status")
    triggering_findings: list[TriggeringFinding] = Field(default_factory=list, description="Top 1–3 findings that drove this recommendation")
    recommended_action: str = Field(..., description="Actionable recommendation for the human reviewer")

    @field_validator("status")
    @classmethod
    def validate_non_adjudication_status(cls, v: ReviewStatus) -> ReviewStatus:
        str_val = str(v.value if isinstance(v, ReviewStatus) else v).upper()
        if str_val in PROHIBITED_DECISION_TERMS:
            raise ValueError(
                f"Prohibited adjudication status '{str_val}'. "
                f"ClaimLens strictly requires review-oriented statuses only: "
                f"{[s.value for s in ReviewStatus]}"
            )
        return v

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


# ── Recommendation Engine ────────────────────────────────────────────────

class ReviewRecommendationEngine:
    """Evaluates evidence findings and assigns deterministic human review workflow statuses."""

    def evaluate(
        self,
        policy_findings: Optional[list[Union[PolicyFinding, dict[str, Any]]]] = None,
        contradictions: Optional[list[Union[ContradictionFinding, dict[str, Any]]]] = None,
        completeness_findings: Optional[list[Union[CompletenessFinding, dict[str, Any]]]] = None,
    ) -> ReviewRecommendation:
        """Deterministically determine review status based on the strict decision hierarchy:

        1. IF required evidence is missing -> REQUEST_INFORMATION
        2. ELSE IF HIGH severity contradictions exist -> REQUEST_INFORMATION
        3. ELSE IF material policy rule failures exist -> ESCALATE_FOR_HUMAN_REVIEW
        4. ELSE IF medium severity contradictions or policy warnings exist -> ESCALATE_FOR_HUMAN_REVIEW
        5. ELSE IF evidence is complete and policy findings are satisfactory -> READY_FOR_REVIEW
        """
        p_findings = self._normalize_policy_findings(policy_findings or [])
        c_findings = self._normalize_contradictions(contradictions or [])
        comp_findings = self._normalize_completeness(completeness_findings or [])

        # Step 1: Check for missing evidence (Highest Priority)
        missing_docs = [
            f for f in comp_findings
            if str(f.status).upper() == CompletenessStatus.MISSING.value or f.status == CompletenessStatus.MISSING
        ]
        if missing_docs:
            triggering = []
            for m in missing_docs[:3]:
                triggering.append(TriggeringFinding(
                    finding_type="MISSING_EVIDENCE",
                    title=f"Missing Required Document: {m.required_document}",
                    detail=m.message,
                    source=f"Clause {m.clause_id}",
                    severity="MISSING",
                ))
            doc_names = ", ".join(m.required_document for m in missing_docs)
            return ReviewRecommendation(
                status=ReviewStatus.REQUEST_INFORMATION,
                reason=f"Required evidence ({doc_names}) is missing from the claim submission under applicable policy terms.",
                triggering_findings=triggering,
                recommended_action=ACTION_REQUEST_INFORMATION,
            )

        # Step 2: Check for HIGH severity contradictions
        high_contradictions = [
            c for c in c_findings
            if str(c.severity).upper() == ContradictionSeverity.HIGH.value or c.severity == ContradictionSeverity.HIGH
        ]
        if high_contradictions:
            triggering = []
            for c in high_contradictions[:3]:
                field_label = str(c.field_name).replace("_", " ").title()
                triggering.append(TriggeringFinding(
                    finding_type="CONTRADICTION",
                    title=f"Factual Contradiction: {field_label}",
                    detail=c.message,
                    source=f"{c.document_a} vs {c.document_b}",
                    severity="HIGH",
                ))
            count_str = f"{len(high_contradictions)} high-severity evidence contradiction(s)"
            return ReviewRecommendation(
                status=ReviewStatus.REQUEST_INFORMATION,
                reason=f"{count_str} detected between submitted claim documents. Clarification is required.",
                triggering_findings=triggering,
                recommended_action=ACTION_REQUEST_INFORMATION,
            )

        # Step 3: Check for policy rule failures (FAIL)
        failed_policy = [
            p for p in p_findings
            if str(p.status).upper() == RuleFindingStatus.FAIL.value or p.status == RuleFindingStatus.FAIL
        ]
        if failed_policy:
            triggering = []
            for p in failed_policy[:3]:
                triggering.append(TriggeringFinding(
                    finding_type="POLICY_FAILURE",
                    title=f"Policy Condition Not Met: Clause {p.clause_id} ({p.title})",
                    detail=p.message,
                    source=f"Clause {p.clause_id}",
                    severity="FAIL",
                ))
            return ReviewRecommendation(
                status=ReviewStatus.ESCALATE_FOR_HUMAN_REVIEW,
                reason=f"Policy rule conditions were not satisfied based on current claim facts (Clause {failed_policy[0].clause_id}).",
                triggering_findings=triggering,
                recommended_action=ACTION_ESCALATE_FOR_HUMAN_REVIEW,
            )

        # Step 4: Check for medium/low contradictions, incomplete evidence, or policy warnings
        warning_policy = [
            p for p in p_findings
            if str(p.status).upper() in (RuleFindingStatus.WARNING.value, RuleFindingStatus.INSUFFICIENT_EVIDENCE.value)
        ]
        med_contradictions = [
            c for c in c_findings
            if str(c.severity).upper() in (ContradictionSeverity.MEDIUM.value, ContradictionSeverity.LOW.value)
        ]
        incomplete_docs = [
            f for f in comp_findings
            if str(f.status).upper() == CompletenessStatus.INCOMPLETE.value
        ]

        if warning_policy or med_contradictions or incomplete_docs:
            triggering = []
            for c in med_contradictions[:2]:
                triggering.append(TriggeringFinding(
                    finding_type="CONTRADICTION",
                    title=f"Discrepancy: {str(c.field_name).replace('_', ' ').title()}",
                    detail=c.message,
                    source=f"{c.document_a} vs {c.document_b}",
                    severity=str(c.severity),
                ))
            for p in warning_policy[:2]:
                triggering.append(TriggeringFinding(
                    finding_type="POLICY_WARNING",
                    title=f"Policy Warning: Clause {p.clause_id} ({p.title})",
                    detail=p.message,
                    source=f"Clause {p.clause_id}",
                    severity=str(p.status),
                ))
            for inc in incomplete_docs[:2]:
                triggering.append(TriggeringFinding(
                    finding_type="INCOMPLETE_EVIDENCE",
                    title=f"Incomplete Evidence: {inc.required_document}",
                    detail=inc.message,
                    source=f"Clause {inc.clause_id}",
                    severity="INCOMPLETE",
                ))

            return ReviewRecommendation(
                status=ReviewStatus.ESCALATE_FOR_HUMAN_REVIEW,
                reason="Minor discrepancies or policy conditions requiring human reviewer assessment.",
                triggering_findings=triggering[:3],
                recommended_action=ACTION_ESCALATE_FOR_HUMAN_REVIEW,
            )

        # Step 5: Clean & Complete Claim -> READY_FOR_REVIEW
        return ReviewRecommendation(
            status=ReviewStatus.READY_FOR_REVIEW,
            reason="Evidence package is complete, internally consistent, and satisfies preliminary policy criteria.",
            triggering_findings=[
                TriggeringFinding(
                    finding_type="VERIFIED_COMPLETE",
                    title="All Required Evidence Present",
                    detail="Submitted documentation satisfies applicable policy requirements.",
                    source="Policy Schedule",
                    severity="PASS",
                )
            ],
            recommended_action=ACTION_READY_FOR_REVIEW,
        )

    # ── Helpers for normalizing input types ───────────────────────────────

    def _normalize_policy_findings(
        self, findings: list[Union[PolicyFinding, dict[str, Any]]]
    ) -> list[PolicyFinding]:
        norm = []
        for f in findings:
            if isinstance(f, PolicyFinding):
                norm.append(f)
            elif isinstance(f, dict):
                try:
                    norm.append(PolicyFinding(**f))
                except Exception:
                    pass
        return norm

    def _normalize_contradictions(
        self, contradictions: list[Union[ContradictionFinding, dict[str, Any]]]
    ) -> list[ContradictionFinding]:
        norm = []
        for c in contradictions:
            if isinstance(c, ContradictionFinding):
                norm.append(c)
            elif isinstance(c, dict):
                try:
                    norm.append(ContradictionFinding(**c))
                except Exception:
                    pass
        return norm

    def _normalize_completeness(
        self, completeness: list[Union[CompletenessFinding, dict[str, Any]]]
    ) -> list[CompletenessFinding]:
        norm = []
        for cf in completeness:
            if isinstance(cf, CompletenessFinding):
                norm.append(cf)
            elif isinstance(cf, dict):
                try:
                    norm.append(CompletenessFinding(**cf))
                except Exception:
                    pass
        return norm
