"""Unit tests for the Review Recommendation Engine (Milestone 7).

Tests deterministic review recommendation logic, decision hierarchy,
and strict non-adjudication boundary enforcement.
"""

import pytest
from src.review.recommendation_engine import (
    ReviewRecommendationEngine,
    ReviewRecommendation,
    ReviewStatus,
    PROHIBITED_DECISION_TERMS,
    ACTION_READY_FOR_REVIEW,
    ACTION_REQUEST_INFORMATION,
    ACTION_ESCALATE_FOR_HUMAN_REVIEW,
)
from src.rules.policy_rules import PolicyFinding, RuleFindingStatus
from src.analysis.contradiction_detector import (
    ContradictionFinding,
    ContradictionCategory,
    ContradictionSeverity,
)
from src.analysis.completeness_checker import (
    CompletenessFinding,
    CompletenessStatus,
)


@pytest.fixture
def engine():
    return ReviewRecommendationEngine()


class TestReviewRecommendationEngine:
    def test_clean_claim_ready_for_review(self, engine):
        """Clean claim with no contradictions, complete documents, and passing rules -> READY_FOR_REVIEW."""
        policy_findings = [
            PolicyFinding(
                rule_id="coverage_period",
                clause_id="1.1",
                title="Policy Period",
                status=RuleFindingStatus.PASS,
                category="Period",
                message="Within period",
            ),
            PolicyFinding(
                rule_id="required_documents",
                clause_id="7.1",
                title="Required Docs",
                status=RuleFindingStatus.PASS,
                category="Documents",
                message="All docs present",
            ),
        ]
        completeness = [
            CompletenessFinding(
                requirement_id="req_cf",
                clause_id="7.1",
                required_document="Claim Form",
                status=CompletenessStatus.PRESENT,
                message="Claim Form present",
            ),
            CompletenessFinding(
                requirement_id="req_est",
                clause_id="7.1",
                required_document="Repair Estimate",
                status=CompletenessStatus.PRESENT,
                message="Repair Estimate present",
            ),
        ]

        rec = engine.evaluate(
            policy_findings=policy_findings,
            contradictions=[],
            completeness_findings=completeness,
        )

        assert rec.status == ReviewStatus.READY_FOR_REVIEW
        assert rec.recommended_action == ACTION_READY_FOR_REVIEW
        assert "complete" in rec.reason.lower()

    def test_missing_evidence_request_information(self, engine):
        """Missing mandatory document (e.g. FIR in Theft) -> REQUEST_INFORMATION."""
        completeness = [
            CompletenessFinding(
                requirement_id="req_cf",
                clause_id="7.2",
                required_document="Claim Form",
                status=CompletenessStatus.PRESENT,
                message="Claim Form present",
            ),
            CompletenessFinding(
                requirement_id="req_fir",
                clause_id="7.2",
                required_document="FIR",
                status=CompletenessStatus.MISSING,
                message="Mandatory First Information Report (FIR) is missing under Clause 3.2 and 7.2",
            ),
        ]

        rec = engine.evaluate(
            policy_findings=[],
            contradictions=[],
            completeness_findings=completeness,
        )

        assert rec.status == ReviewStatus.REQUEST_INFORMATION
        assert rec.recommended_action == ACTION_REQUEST_INFORMATION
        assert "FIR" in rec.reason or "missing" in rec.reason.lower()
        assert len(rec.triggering_findings) >= 1
        assert rec.triggering_findings[0].finding_type == "MISSING_EVIDENCE"
        assert rec.triggering_findings[0].severity == "MISSING"

    def test_high_severity_contradiction_request_information(self, engine):
        """High severity contradiction (e.g. date mismatch or amount discrepancy) -> REQUEST_INFORMATION."""
        completeness = [
            CompletenessFinding(
                requirement_id="req_cf",
                clause_id="7.1",
                required_document="Claim Form",
                status=CompletenessStatus.PRESENT,
                message="Claim Form present",
            ),
        ]
        contradictions = [
            ContradictionFinding(
                contradiction_id="CTR-001",
                category=ContradictionCategory.INCIDENT_DATE_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="incident_date",
                document_a="claim_form.pdf",
                document_b="repair_estimate.pdf",
                value_a="2026-08-10",
                value_b="2026-08-14",
                evidence_a="10 August 2026",
                evidence_b="14 August 2026",
                message="Incident date mismatch: 10 Aug vs 14 Aug",
            ),
            ContradictionFinding(
                contradiction_id="CTR-002",
                category=ContradictionCategory.CLAIM_AMOUNT_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="claimed_amount",
                document_a="claim_form.pdf",
                document_b="repair_estimate.pdf",
                value_a=85000.0,
                value_b=92000.0,
                evidence_a="Rs. 85,000",
                evidence_b="Rs. 92,000",
                message="Amount mismatch: 85000 vs 92000",
            ),
        ]

        rec = engine.evaluate(
            policy_findings=[],
            contradictions=contradictions,
            completeness_findings=completeness,
        )

        assert rec.status == ReviewStatus.REQUEST_INFORMATION
        assert rec.recommended_action == ACTION_REQUEST_INFORMATION
        assert len(rec.triggering_findings) == 2
        assert rec.triggering_findings[0].finding_type == "CONTRADICTION"
        assert rec.triggering_findings[0].severity == "HIGH"

    def test_material_policy_rule_failure_escalate(self, engine):
        """Failing policy rule -> ESCALATE_FOR_HUMAN_REVIEW."""
        policy_findings = [
            PolicyFinding(
                rule_id="coverage_period",
                clause_id="1.1",
                title="Coverage Period",
                status=RuleFindingStatus.FAIL,
                category="Period",
                message="Incident date outside active policy coverage dates.",
            ),
        ]
        completeness = [
            CompletenessFinding(
                requirement_id="req_cf",
                clause_id="7.1",
                required_document="Claim Form",
                status=CompletenessStatus.PRESENT,
                message="Claim Form present",
            ),
        ]

        rec = engine.evaluate(
            policy_findings=policy_findings,
            contradictions=[],
            completeness_findings=completeness,
        )

        assert rec.status == ReviewStatus.ESCALATE_FOR_HUMAN_REVIEW
        assert rec.recommended_action == ACTION_ESCALATE_FOR_HUMAN_REVIEW
        assert len(rec.triggering_findings) == 1
        assert rec.triggering_findings[0].finding_type == "POLICY_FAILURE"

    def test_priority_missing_evidence_over_high_contradiction(self, engine):
        """Missing evidence has higher priority than high contradiction."""
        completeness = [
            CompletenessFinding(
                requirement_id="req_fir",
                clause_id="7.2",
                required_document="FIR",
                status=CompletenessStatus.MISSING,
                message="Missing FIR",
            ),
        ]
        contradictions = [
            ContradictionFinding(
                contradiction_id="CTR-001",
                category=ContradictionCategory.INCIDENT_DATE_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="incident_date",
                document_a="claim_form.pdf",
                document_b="repair_estimate.pdf",
                message="Mismatch",
            ),
        ]

        rec = engine.evaluate(
            policy_findings=[],
            contradictions=contradictions,
            completeness_findings=completeness,
        )

        assert rec.status == ReviewStatus.REQUEST_INFORMATION
        assert rec.triggering_findings[0].finding_type == "MISSING_EVIDENCE"

    def test_priority_high_contradiction_over_policy_failure(self, engine):
        """High contradiction triggers REQUEST_INFORMATION over general policy escalation."""
        contradictions = [
            ContradictionFinding(
                contradiction_id="CTR-001",
                category=ContradictionCategory.INCIDENT_DATE_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="incident_date",
                document_a="claim_form.pdf",
                document_b="repair_estimate.pdf",
                message="Mismatch",
            ),
        ]
        policy_findings = [
            PolicyFinding(
                rule_id="notification_window",
                clause_id="6.1",
                title="Notification Window",
                status=RuleFindingStatus.FAIL,
                category="Timeline",
                message="Late notification",
            ),
        ]
        completeness = [
            CompletenessFinding(
                requirement_id="req_cf",
                clause_id="7.1",
                required_document="Claim Form",
                status=CompletenessStatus.PRESENT,
                message="Present",
            ),
        ]

        rec = engine.evaluate(
            policy_findings=policy_findings,
            contradictions=contradictions,
            completeness_findings=completeness,
        )

        assert rec.status == ReviewStatus.REQUEST_INFORMATION
        assert rec.triggering_findings[0].finding_type == "CONTRADICTION"

    def test_prohibited_terms_rejected(self):
        """Ensures prohibited final decision terms cannot be assigned as ReviewStatus."""
        for term in PROHIBITED_DECISION_TERMS:
            with pytest.raises(ValueError):
                ReviewRecommendation(
                    status=term,  # type: ignore
                    reason="Invalid status test",
                    triggering_findings=[],
                    recommended_action="Test action",
                )
