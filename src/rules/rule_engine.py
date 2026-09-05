"""Policy Rule Engine for ClaimLens (Milestone 5).

Deterministic evaluation orchestrator executing policy rules against extracted
claim facts and document inventories without making final claim determinations.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from src.models import ExtractedFact
from src.rules.policy_rules import (
    PolicyFinding,
    RuleFindingStatus,
    FactUsed,
    extract_fact_dict,
    check_coverage_period,
    check_covered_vehicle,
    check_accident_coverage,
    check_repair_settlement,
    check_theft_coverage,
    check_fir_requirement,
    check_idv_valuation,
    check_notification_window,
    check_required_documents,
    check_explicit_exclusions,
)

logger = logging.getLogger("claimlens.rule_engine")


class RuleEvaluationSummary(BaseModel):
    """Aggregated outcome metrics across evaluated policy rules."""
    total_rules_checked: int = 0
    pass_count: int = 0
    fail_count: int = 0
    warning_count: int = 0
    insufficient_evidence_count: int = 0
    not_applicable_count: int = 0


class PolicyEvaluationResult(BaseModel):
    """Complete auditable rule evaluation payload."""
    claim_id: Optional[str] = None
    findings: list[PolicyFinding] = Field(default_factory=list)
    summary: RuleEvaluationSummary = Field(default_factory=RuleEvaluationSummary)


class PolicyRuleEngine:
    """Orchestrator for deterministic motor policy rule evaluations."""

    def __init__(self, default_idv: Optional[float] = None) -> None:
        self.default_idv = default_idv

    def evaluate(
        self,
        facts: Union[list[ExtractedFact], dict[str, Any], None],
        documents: Optional[list[str]] = None,
        claim_id: Optional[str] = None,
        retrieved_clauses: Optional[list[Any]] = None,
    ) -> PolicyEvaluationResult:
        """Execute deterministic policy rules against claim facts and documents.

        Args:
            facts: List of ExtractedFact objects, or key-value dict of claim facts.
            documents: Optional list of document names/types in the claim dossier.
            claim_id: Optional claim identifier for audit reference.
            retrieved_clauses: Optional list of semantically retrieved clauses.

        Returns:
            PolicyEvaluationResult with structured findings and summary metrics.
        """
        fact_dict, fact_objs = extract_fact_dict(facts)

        if not claim_id and "claim_id" in fact_dict:
            claim_id = str(fact_dict["claim_id"])

        findings: list[PolicyFinding] = []

        # 1. Coverage Period (Clause 1.1)
        findings.append(check_coverage_period(fact_dict, fact_objs))

        # 2. Covered Vehicle Identification (Clause 1.2)
        findings.append(check_covered_vehicle(fact_dict, fact_objs))

        # 3. Accidental Damage Coverage (Clause 2.1)
        findings.append(check_accident_coverage(fact_dict, fact_objs))

        # 4. Repair Settlement Assessment (Clause 2.2)
        findings.append(check_repair_settlement(fact_dict, fact_objs, documents=documents))

        # 5. Total Loss Due to Theft (Clause 3.1)
        findings.append(check_theft_coverage(fact_dict, fact_objs))

        # 6. FIR Requirement for Theft Claims (Clause 3.2)
        findings.append(check_fir_requirement(fact_dict, fact_objs, documents=documents))

        # 7. Policy Exclusions (Clauses 4.1, 4.2, 4.3)
        findings.extend(check_explicit_exclusions(fact_dict, fact_objs))

        # 8. Insured Declared Value / Claim Amount (Clauses 5.1 & 5.2)
        findings.append(check_idv_valuation(fact_dict, fact_objs, default_idv=self.default_idv))

        # 9. Claim Notification Window (Clauses 6.1 & 6.2)
        findings.append(check_notification_window(fact_dict, fact_objs))

        # 10. Required Document Checklist (Clauses 7.1 & 7.2)
        findings.append(check_required_documents(fact_dict, fact_objs, documents=documents))

        # Compute summary metrics
        summary = RuleEvaluationSummary(
            total_rules_checked=len(findings),
            pass_count=sum(1 for f in findings if f.status == RuleFindingStatus.PASS),
            fail_count=sum(1 for f in findings if f.status == RuleFindingStatus.FAIL),
            warning_count=sum(1 for f in findings if f.status == RuleFindingStatus.WARNING),
            insufficient_evidence_count=sum(
                1 for f in findings if f.status == RuleFindingStatus.INSUFFICIENT_EVIDENCE
            ),
            not_applicable_count=sum(
                1 for f in findings if f.status == RuleFindingStatus.NOT_APPLICABLE
            ),
        )

        logger.info(
            f"Evaluated {len(findings)} policy rules for claim {claim_id or 'UNKNOWN'}: "
            f"{summary.pass_count} PASS, {summary.fail_count} FAIL, {summary.warning_count} WARNING, "
            f"{summary.insufficient_evidence_count} INSUFFICIENT, {summary.not_applicable_count} N/A"
        )

        return PolicyEvaluationResult(
            claim_id=claim_id,
            findings=findings,
            summary=summary,
        )
