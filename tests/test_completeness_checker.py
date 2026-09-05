"""Unit tests for the Completeness Checker (Milestone 6).

Tests policy-grounded document requirement checks (Clauses 7.1, 7.2, 3.2),
claim type determination, and missing document status reporting.
"""

import pytest
from src.analysis.completeness_checker import (
    CompletenessChecker,
    CompletenessFinding,
    CompletenessStatus,
    determine_claim_type,
)
from src.models import ExtractedFact


@pytest.fixture
def checker():
    return CompletenessChecker()


class TestCompletenessChecker:
    def test_determine_claim_type_accident(self):
        """Accident keywords and document types classify as ACCIDENT."""
        facts = [
            ExtractedFact(
                field_name="incident_description",
                value="Skidded on wet road and hit guardrail",
                evidence_text="Skidded on wet road",
            )
        ]
        assert determine_claim_type(facts) == "ACCIDENT"

        # Via dict
        assert determine_claim_type({"incident_type": "Accident / Collision"}) == "ACCIDENT"

    def test_determine_claim_type_theft(self):
        """Theft keywords and FIR document types classify as THEFT."""
        facts = [
            ExtractedFact(
                field_name="incident_description",
                value="Vehicle was stolen from overnight parking outside apartment",
                evidence_text="stolen from parking",
            )
        ]
        assert determine_claim_type(facts) == "THEFT"

        # Via documents list with FIR
        assert determine_claim_type(documents=["fir_police_report.pdf"]) == "THEFT"

    def test_accident_claim_complete_documents(self, checker):
        """Accident claim with Claim Form, Repair Estimate, and Incident Description is fully complete."""
        facts = [
            ExtractedFact(
                field_name="incident_description",
                value="Front collision with tree",
                evidence_text="Front collision with tree",
            ),
            ExtractedFact(
                field_name="claimed_amount",
                value=45000.0,
                evidence_text="Claimed: 45000",
            ),
        ]
        documents = ["claim_form.pdf", "repair_estimate.pdf"]

        findings = checker.check(facts=facts, documents=documents)
        assert len(findings) == 3
        # All three must be PRESENT
        for f in findings:
            assert f.status == CompletenessStatus.PRESENT
            assert f.clause_id == "7.1"

    def test_accident_claim_missing_repair_estimate(self, checker):
        """Accident claim without Repair Estimate must flag MISSING under Clause 7.1."""
        facts = [
            ExtractedFact(
                field_name="incident_description",
                value="Front collision with tree",
                evidence_text="Front collision",
            )
        ]
        documents = ["claim_form.pdf"]

        findings = checker.check(facts=facts, documents=documents)
        estimate_findings = [f for f in findings if "Repair" in f.required_document]
        assert len(estimate_findings) == 1
        assert estimate_findings[0].status == CompletenessStatus.MISSING
        assert estimate_findings[0].clause_id == "7.1"

    def test_theft_claim_missing_fir(self, checker):
        """Theft claim without FIR must flag MISSING under Clause 7.2."""
        facts = [
            ExtractedFact(
                field_name="incident_description",
                value="Vehicle stolen from garage",
                evidence_text="Vehicle stolen",
            )
        ]
        documents = ["claim_form.pdf"]

        findings = checker.check(facts=facts, documents=documents)
        fir_findings = [f for f in findings if "FIR" in f.required_document]
        assert len(fir_findings) == 1
        assert fir_findings[0].status == CompletenessStatus.MISSING
        assert fir_findings[0].clause_id == "7.2"

    def test_theft_claim_with_fir_present(self, checker):
        """Theft claim with FIR and Claim Form must mark both PRESENT."""
        facts = [
            ExtractedFact(
                field_name="incident_description",
                value="Vehicle stolen from parking lot",
                evidence_text="stolen from parking lot",
            )
        ]
        documents = ["claim_form.pdf", "fir_station_report.pdf"]

        findings = checker.check(facts=facts, documents=documents)
        fir_findings = [f for f in findings if "FIR" in f.required_document]
        assert len(fir_findings) == 1
        assert fir_findings[0].status == CompletenessStatus.PRESENT

    def test_missing_incident_description(self, checker):
        """When incident description is omitted, it must be marked MISSING."""
        facts = [
            ExtractedFact(
                field_name="vehicle_registration",
                value="KA01AB1234",
                evidence_text="KA01AB1234",
            )
        ]
        documents = ["claim_form.pdf"]

        findings = checker.check(facts=facts, documents=documents)
        desc_findings = [f for f in findings if "Incident Description" in f.required_document]
        assert len(desc_findings) == 1
        assert desc_findings[0].status == CompletenessStatus.MISSING
