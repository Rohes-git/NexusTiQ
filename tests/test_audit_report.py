"""Unit tests for Claims Evidence Audit Report generation (Milestone 7).

Tests structure, evidence provenance preservation, policy citations,
and mandatory non-adjudication legal disclaimer presence.
"""

import pytest
from src.report.audit_report import (
    AuditReport,
    AuditReportGenerator,
    EvidenceReference,
    ClaimSummaryDetails,
    STANDARD_DISCLAIMER,
)
from src.review.recommendation_engine import (
    ReviewRecommendationEngine,
    ReviewStatus,
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
from src.retrieval.grounding import GroundedClause
from src.models import ExtractedFact


@pytest.fixture
def sample_report_generator():
    return AuditReportGenerator()


class TestAuditReport:
    def test_audit_report_structure_and_sections(self, sample_report_generator):
        """Audit report must contain all expected top-level sections."""
        facts = {
            "policy_number": "POL-2026-98765",
            "vehicle_registration": "MH-02-CD-5678",
            "incident_date": "2026-08-10",
            "claimed_amount": 45000.0,
        }
        documents = ["claim_form.pdf", "repair_estimate.pdf"]
        clauses = [
            GroundedClause(
                clause_id="1.1",
                section="Section 1",
                title="Policy Period",
                text="Coverage is active during policy term.",
                similarity_score=0.92,
                reason="Relevant to policy period validity and incident date verification.",
            )
        ]
        policy_findings = [
            PolicyFinding(
                rule_id="coverage_period",
                clause_id="1.1",
                title="Policy Period",
                status=RuleFindingStatus.PASS,
                category="Period",
                message="Incident is within valid policy period.",
            )
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

        report = sample_report_generator.generate_report(
            claim_id="CLM-001",
            facts=facts,
            documents=documents,
            retrieved_clauses=clauses,
            policy_findings=policy_findings,
            contradictions=[],
            completeness_findings=completeness,
        )

        assert isinstance(report, AuditReport)
        assert report.claim_id == "CLM-001"
        assert report.claim_summary.vehicle_registration == "MH-02-CD-5678"
        assert len(report.document_inventory) == 2
        assert len(report.policy_clauses) == 1
        assert len(report.policy_findings) == 1
        assert len(report.completeness_findings) == 2
        assert report.recommendation.status == ReviewStatus.READY_FOR_REVIEW

    def test_evidence_provenance_retained(self, sample_report_generator):
        """Every fact in the audit report retains its document, page, and exact quotation."""
        facts = [
            ExtractedFact(
                field_name="incident_location",
                value="MG Road, Pune",
                page_number=1,
                evidence_text="Location of Incident: MG Road, Pune",
            ),
            ExtractedFact(
                field_name="driver_name",
                value="Jane Doe",
                page_number=1,
                evidence_text="Name of Driver: Jane Doe",
            ),
        ]

        report = sample_report_generator.generate_report(
            claim_id="CLM-001",
            facts=facts,
            documents=["claim_form.pdf"],
        )

        assert len(report.extracted_facts) == 2
        assert len(report.evidence_references) >= 2
        for ref in report.evidence_references:
            assert ref.document_name == "claim_form.pdf"
            assert ref.page_number >= 1
            assert len(ref.evidence_text) > 5

    def test_policy_clause_references_retained(self, sample_report_generator):
        """Policy clause IDs and titles are preserved for auditability."""
        clauses = [
            GroundedClause(
                clause_id="2.1",
                section="Section 2",
                title="Accidental Damage",
                text="Direct physical loss or damage.",
                similarity_score=0.88,
                reason="Relevant to accidental damage, collision, and external impact coverage.",
            )
        ]
        report = sample_report_generator.generate_report(
            claim_id="CLM-001",
            retrieved_clauses=clauses,
        )

        assert len(report.policy_clauses) == 1
        assert report.policy_clauses[0].clause_id == "2.1"
        assert "Accidental" in report.policy_clauses[0].title

    def test_mandatory_disclaimer_present(self, sample_report_generator):
        """Report must contain the standard non-adjudication legal disclaimer."""
        report = sample_report_generator.generate_report(claim_id="CLM-001")
        assert report.disclaimer == STANDARD_DISCLAIMER
        assert "does not make final insurance claim decisions" in report.disclaimer
        assert "human claims investigator" in report.disclaimer

    def test_json_serialization(self, sample_report_generator):
        """AuditReport models serialize cleanly to dictionary and JSON."""
        facts = [
            ExtractedFact(
                field_name="policy_number",
                value="POL-123",
                page_number=1,
                evidence_text="Policy: POL-123",
            )
        ]
        report = sample_report_generator.generate_report(
            claim_id="CLM-001",
            facts=facts,
            documents=["claim_form.pdf"],
        )
        data = report.model_dump()
        assert isinstance(data, dict)
        assert data["claim_id"] == "CLM-001"
        assert data["disclaimer"] == STANDARD_DISCLAIMER
        assert len(data["evidence_references"]) >= 1
