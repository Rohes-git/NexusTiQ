"""Integration tests for Evidence Review Engine & /api/analyze-evidence (Milestone 6).

Verifies end-to-end evidence analysis, multi-document cross-checks, demo claims,
and adherence to the strict non-adjudication boundary (never outputs final decisions).
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.analysis.evidence_review import EvidenceReviewEngine, EvidenceReviewResult
from src.analysis.contradiction_detector import ContradictionSeverity
from src.analysis.completeness_checker import CompletenessStatus
from src.models import ExtractedFact

client = TestClient(app)


class TestEvidenceReviewEngine:
    @pytest.fixture
    def engine(self):
        return EvidenceReviewEngine()

    def test_clm001_accident_consistent_and_complete(self, engine):
        """CLM-001: Valid accident claim with matching documents and full completeness."""
        doc1 = {
            "document_name": "CLM-001_claim_form.pdf",
            "document_type": "claim_form",
            "facts": [
                {"field_name": "incident_type", "value": "Accident", "raw_value": "Accident", "evidence_text": "Type: Accident"},
                {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20 August 2026", "evidence_text": "Date: 20 August 2026"},
                {"field_name": "vehicle_registration", "value": "KA01AB1234", "raw_value": "KA-01-AB-1234", "evidence_text": "Reg: KA-01-AB-1234"},
                {"field_name": "vehicle_make", "value": "Hyundai", "raw_value": "Hyundai", "evidence_text": "Make: Hyundai"},
                {"field_name": "vehicle_model", "value": "Creta", "raw_value": "Creta", "evidence_text": "Model: Creta"},
                {"field_name": "claimed_amount", "value": 78000.0, "raw_value": "Rs. 78,000", "evidence_text": "Amount: Rs. 78,000"},
                {"field_name": "incident_description", "value": "Front bumper collision", "raw_value": "Front bumper collision", "evidence_text": "Front bumper collision"},
            ],
        }
        doc2 = {
            "document_name": "CLM-001_repair_estimate.pdf",
            "document_type": "repair_estimate",
            "facts": [
                {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20/08/2026", "evidence_text": "Date of Loss: 20/08/2026"},
                {"field_name": "vehicle_registration", "value": "KA01AB1234", "raw_value": "KA01AB1234", "evidence_text": "Reg: KA01AB1234"},
                {"field_name": "vehicle_make", "value": "Hyundai", "raw_value": "Hyundai", "evidence_text": "Make: Hyundai"},
                {"field_name": "vehicle_model", "value": "Creta", "raw_value": "Creta", "evidence_text": "Model: Creta"},
                {"field_name": "repair_estimate_amount", "value": 78000.0, "raw_value": "₹78,000", "evidence_text": "Total Estimate: ₹78,000"},
            ],
        }

        result = engine.analyze(
            claim_id="CLM-001",
            facts=[doc1, doc2],
            documents=["CLM-001_claim_form.pdf", "CLM-001_repair_estimate.pdf"],
        )

        assert isinstance(result, EvidenceReviewResult)
        assert result.claim_id == "CLM-001"
        assert result.claim_type == "ACCIDENT"
        assert len(result.contradictions) == 0
        assert result.summary["total_contradictions"] == 0
        assert result.summary["missing_documents_count"] == 0
        assert len(result.consistent_fields) >= 3

    def test_clm002_theft_missing_fir(self, engine):
        """CLM-002: Theft claim missing police FIR (Clause 7.2 requirement)."""
        doc1 = {
            "document_name": "CLM-002_claim_form.pdf",
            "document_type": "claim_form",
            "facts": [
                {"field_name": "incident_type", "value": "Theft", "raw_value": "Theft", "evidence_text": "Type: Theft"},
                {"field_name": "incident_description", "value": "Vehicle stolen from residential parking", "raw_value": "stolen from parking", "evidence_text": "stolen from parking"},
                {"field_name": "vehicle_registration", "value": "MH02CD5678", "raw_value": "MH-02-CD-5678", "evidence_text": "Reg: MH-02-CD-5678"},
                {"field_name": "claimed_amount", "value": 550000.0, "raw_value": "5,50,000", "evidence_text": "IDV: 5,50,000"},
            ],
        }

        result = engine.analyze(
            claim_id="CLM-002",
            facts=[doc1],
            documents=["CLM-002_claim_form.pdf"],
        )

        assert result.claim_type == "THEFT"
        missing_fir = [c for c in result.completeness if "FIR" in c.required_document]
        assert len(missing_fir) == 1
        assert missing_fir[0].status == CompletenessStatus.MISSING
        assert missing_fir[0].clause_id == "7.2"
        assert result.summary["missing_documents_count"] >= 1

    def test_clm003_amount_contradiction(self, engine):
        """CLM-003: Discrepancy between claimed amount and repair estimate."""
        doc1 = {
            "document_name": "CLM-003_claim_form.pdf",
            "document_type": "claim_form",
            "facts": [
                {"field_name": "incident_type", "value": "Accident", "evidence_text": "Accident"},
                {"field_name": "claimed_amount", "value": 85000.0, "raw_value": "Rs. 85,000", "evidence_text": "Claimed: Rs. 85,000", "page_number": 1},
                {"field_name": "incident_description", "value": "Rear end collision", "evidence_text": "Rear end collision"},
            ],
        }
        doc2 = {
            "document_name": "CLM-003_repair_estimate.pdf",
            "document_type": "repair_estimate",
            "facts": [
                {"field_name": "repair_estimate_amount", "value": 62000.0, "raw_value": "₹62,000", "evidence_text": "Estimate Total: ₹62,000", "page_number": 2},
            ],
        }

        result = engine.analyze(
            claim_id="CLM-003",
            facts=[doc1, doc2],
            documents=["CLM-003_claim_form.pdf", "CLM-003_repair_estimate.pdf"],
        )

        assert result.summary["total_contradictions"] >= 1
        amount_mismatch = [c for c in result.contradictions if "AMOUNT" in c.category]
        assert len(amount_mismatch) == 1
        assert amount_mismatch[0].severity == ContradictionSeverity.HIGH
        assert amount_mismatch[0].value_a == 85000.0
        assert amount_mismatch[0].value_b == 62000.0
        assert amount_mismatch[0].page_a == 1
        assert amount_mismatch[0].page_b == 2

    def test_non_adjudication_boundary(self, engine):
        """The evidence analysis engine strictly does not adjudicate claims."""
        result = engine.analyze(
            claim_id="CLM-TEST",
            facts=[
                ExtractedFact(field_name="claimed_amount", value=100000.0, evidence_text="100000"),
                ExtractedFact(field_name="repair_estimate_amount", value=50000.0, evidence_text="50000"),
            ],
            documents=["claim.pdf", "estimate.pdf"],
        )

        result_dict = result.model_dump()
        result_json_str = json.dumps(result_dict).upper()

        # Check for banned decision keywords in output fields
        assert "APPROVE" not in result_dict.get("status", "")
        assert "REJECT" not in result_dict.get("status", "")
        assert "DENY" not in result_dict.get("status", "")
        assert "FRAUD" not in result_json_str


class TestAnalyzeEvidenceEndpoint:
    def test_analyze_evidence_api_endpoint(self):
        """POST /api/analyze-evidence returns structured contradictions and completeness findings."""
        payload = {
            "claim_id": "CLM-API-001",
            "documents": ["claim_form.pdf", "fir_report.pdf"],
            "facts": [
                {
                    "document_name": "claim_form.pdf",
                    "document_type": "claim_form",
                    "facts": [
                        {"field_name": "incident_type", "value": "Theft", "raw_value": "Theft", "evidence_text": "Type: Theft"},
                        {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20 August 2026", "evidence_text": "Date: 20 August 2026"},
                        {"field_name": "vehicle_registration", "value": "KA01AB1234", "raw_value": "KA-01-AB-1234", "evidence_text": "Reg: KA-01-AB-1234"},
                        {"field_name": "incident_description", "value": "Vehicle stolen from parking", "raw_value": "stolen from parking", "evidence_text": "stolen from parking"},
                    ],
                },
                {
                    "document_name": "fir_report.pdf",
                    "document_type": "fir",
                    "facts": [
                        {"field_name": "incident_type", "value": "Theft", "raw_value": "Theft", "evidence_text": "Crime: Theft"},
                        {"field_name": "incident_date", "value": "2026-08-15", "raw_value": "15 August 2026", "evidence_text": "Date: 15 August 2026"},
                        {"field_name": "vehicle_registration", "value": "KA01AB1234", "raw_value": "KA-01-AB-1234", "evidence_text": "Reg: KA-01-AB-1234"},
                    ],
                },
            ],
        }

        response = client.post("/api/analyze-evidence", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["claim_id"] == "CLM-API-001"
        assert data["claim_type"] == "THEFT"
        assert len(data["contradictions"]) == 1
        assert data["contradictions"][0]["category"] == "INCIDENT_DATE_MISMATCH"
        assert data["contradictions"][0]["severity"] == "HIGH"
        assert len(data["completeness"]) >= 2
        assert len(data["consistent_fields"]) >= 1
