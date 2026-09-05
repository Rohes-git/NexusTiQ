"""Unit tests for the Contradiction Detector (Milestone 6).

Tests deterministic cross-document fact comparison, evidence provenance preservation,
and severity scoring across motor insurance claim documents.
"""

import pytest
from src.analysis.contradiction_detector import (
    ContradictionDetector,
    ContradictionFinding,
    ContradictionCategory,
    ContradictionSeverity,
    ConsistentFieldFinding,
    DocumentFactRecord,
)
from src.models import ExtractedFact


@pytest.fixture
def detector():
    return ContradictionDetector()


class TestContradictionDetector:
    def test_incident_date_mismatch_detected(self, detector):
        """Discrepancy in incident dates across documents must trigger HIGH severity contradiction."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            incident_date="2026-08-20",
            raw_incident_date="20 August 2026",
            incident_date_evidence="Date of Incident: 20 August 2026",
            incident_date_page=1,
        )
        doc2 = DocumentFactRecord(
            document_name="fir.pdf",
            document_type="fir",
            incident_date="2026-08-18",
            raw_incident_date="18/08/2026",
            incident_date_evidence="Date of Occurrence: 18/08/2026",
            incident_date_page=1,
        )

        findings, consistent = detector.compare_records([doc1, doc2])
        assert len(findings) == 1
        f = findings[0]
        assert f.category == ContradictionCategory.INCIDENT_DATE_MISMATCH
        assert f.severity == ContradictionSeverity.HIGH
        assert f.field_name == "incident_date"
        assert f.value_a == "2026-08-20"
        assert f.value_b == "2026-08-18"
        assert f.document_a == "claim_form.pdf"
        assert f.document_b == "fir.pdf"
        assert "20 August 2026" in f.evidence_a
        assert "18/08/2026" in f.evidence_b

    def test_claim_amount_mismatch_detected(self, detector):
        """Claimed amount vs Repair Estimate amount discrepancy must trigger HIGH severity contradiction."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            claimed_amount=85000.0,
            raw_claimed_amount="Rs. 85,000",
            claimed_amount_evidence="Total Claimed Amount: Rs. 85,000",
            claimed_amount_page=1,
        )
        doc2 = DocumentFactRecord(
            document_name="repair_estimate.pdf",
            document_type="repair_estimate",
            repair_estimate_amount=62000.0,
            raw_repair_estimate_amount="₹62,000",
            repair_estimate_evidence="Grand Total: ₹62,000",
            repair_estimate_page=2,
        )

        findings, _ = detector.compare_records([doc1, doc2])
        amount_mismatches = [f for f in findings if f.category == ContradictionCategory.CLAIM_AMOUNT_MISMATCH]
        assert len(amount_mismatches) == 1
        f = amount_mismatches[0]
        assert f.severity == ContradictionSeverity.HIGH
        assert f.value_a == 85000.0
        assert f.value_b == 62000.0
        assert "₹23,000" in f.message or "23000" in f.message

    def test_vehicle_registration_mismatch_detected(self, detector):
        """Vehicle registration mismatch must trigger HIGH severity contradiction."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            vehicle_registration="KA-01-AB-1234",
            raw_vehicle_registration="KA-01-AB-1234",
            vehicle_registration_evidence="Registration: KA-01-AB-1234",
            vehicle_registration_page=1,
        )
        doc2 = DocumentFactRecord(
            document_name="repair_estimate.pdf",
            document_type="repair_estimate",
            vehicle_registration="MH-02-CD-5678",
            raw_vehicle_registration="MH-02-CD-5678",
            vehicle_registration_evidence="Vehicle Reg No: MH-02-CD-5678",
            vehicle_registration_page=1,
        )

        findings, _ = detector.compare_records([doc1, doc2])
        reg_findings = [f for f in findings if f.category == ContradictionCategory.VEHICLE_REGISTRATION_MISMATCH]
        assert len(reg_findings) == 1
        assert reg_findings[0].severity == ContradictionSeverity.HIGH
        assert reg_findings[0].value_a == "KA01AB1234"
        assert reg_findings[0].value_b == "MH02CD5678"
        assert reg_findings[0].raw_value_a == "KA-01-AB-1234"
        assert reg_findings[0].raw_value_b == "MH-02-CD-5678"

    def test_vehicle_details_make_model_mismatch(self, detector):
        """Vehicle make/model mismatch must trigger MEDIUM severity contradiction."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            vehicle_make="Hyundai",
            vehicle_model="Creta",
            vehicle_make_evidence="Make: Hyundai",
            vehicle_model_evidence="Model: Creta",
        )
        doc2 = DocumentFactRecord(
            document_name="repair_estimate.pdf",
            document_type="repair_estimate",
            vehicle_make="Hyundai",
            vehicle_model="i20",
            vehicle_make_evidence="Make: Hyundai",
            vehicle_model_evidence="Model: i20",
        )

        findings, _ = detector.compare_records([doc1, doc2])
        model_findings = [f for f in findings if f.category == ContradictionCategory.VEHICLE_DETAILS_MISMATCH]
        assert len(model_findings) == 1
        assert model_findings[0].severity == ContradictionSeverity.MEDIUM
        assert model_findings[0].field_name == "vehicle_model"

    def test_notification_date_mismatch(self, detector):
        """Notification date discrepancy must trigger MEDIUM severity contradiction."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            notification_date="2026-08-22",
            raw_notification_date="22 August 2026",
            notification_date_evidence="Date of Claim Notice: 22 August 2026",
        )
        doc2 = DocumentFactRecord(
            document_name="fir.pdf",
            document_type="fir",
            notification_date="2026-08-25",
            raw_notification_date="25/08/2026",
            notification_date_evidence="Intimation Date: 25/08/2026",
        )

        findings, _ = detector.compare_records([doc1, doc2])
        notif_findings = [f for f in findings if f.category == ContradictionCategory.NOTIFICATION_DATE_MISMATCH]
        assert len(notif_findings) == 1
        assert notif_findings[0].severity == ContradictionSeverity.MEDIUM

    def test_date_format_tolerance_no_contradiction(self, detector):
        """Dates that normalize to the same ISO date must NOT be flagged as contradictions."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            incident_date="2026-08-20",
            raw_incident_date="20 August 2026",
            incident_date_evidence="20 August 2026",
        )
        doc2 = DocumentFactRecord(
            document_name="fir.pdf",
            document_type="fir",
            incident_date="2026-08-20",
            raw_incident_date="20/08/2026",
            incident_date_evidence="20/08/2026",
        )

        findings, consistent = detector.compare_records([doc1, doc2])
        assert len(findings) == 0
        date_consistent = [c for c in consistent if c.field_name == "incident_date"]
        assert len(date_consistent) == 1
        assert date_consistent[0].value == "2026-08-20"

    def test_amount_tolerance_no_contradiction(self, detector):
        """Amounts differing by < ₹1.0 (rounding/formatting) must NOT be flagged as contradictions."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            claimed_amount=78000.0,
            raw_claimed_amount="78,000",
        )
        doc2 = DocumentFactRecord(
            document_name="repair_estimate.pdf",
            document_type="repair_estimate",
            repair_estimate_amount=78000.4,
            raw_repair_estimate_amount="78,000.40",
        )

        findings, consistent = detector.compare_records([doc1, doc2])
        assert len(findings) == 0
        amount_consistent = [c for c in consistent if "amount" in c.field_name]
        assert len(amount_consistent) == 1

    def test_missing_fields_do_not_trigger_contradiction(self, detector):
        """A field present in Doc A but absent in Doc B is a completeness issue, not a contradiction."""
        doc1 = DocumentFactRecord(
            document_name="claim_form.pdf",
            document_type="claim_form",
            vehicle_registration="KA-01-AB-1234",
            claimed_amount=50000.0,
        )
        doc2 = DocumentFactRecord(
            document_name="photo.pdf",
            document_type="photo",
            vehicle_registration=None,
            claimed_amount=None,
        )

        findings, _ = detector.compare_records([doc1, doc2])
        assert len(findings) == 0

    def test_detect_from_flat_extracted_facts(self, detector):
        """Detector can detect amount mismatches even from a single flattened fact list containing both amounts."""
        facts = [
            ExtractedFact(
                field_name="claimed_amount",
                value=85000.0,
                raw_value="Rs. 85,000",
                evidence_text="Claimed Amount: Rs. 85,000",
                page_number=1,
            ),
            ExtractedFact(
                field_name="repair_estimate_amount",
                value=62000.0,
                raw_value="Rs. 62,000",
                evidence_text="Repair Total: Rs. 62,000",
                page_number=2,
            ),
        ]

        findings, _ = detector.detect(facts)
        amount_mismatches = [f for f in findings if f.category == ContradictionCategory.CLAIM_AMOUNT_MISMATCH]
        assert len(amount_mismatches) == 1
        assert amount_mismatches[0].severity == ContradictionSeverity.HIGH
