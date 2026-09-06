"""Tests for Quick Demo claims ingestion and end-to-end review pipeline."""

import pytest
from fastapi.testclient import TestClient
from app import app
from src.demo_loader import CLAIM_MAP, load_demo_claim

client = TestClient(app)


def test_get_demo_claim_valid_ids():
    """Ensure all 3 demo claims load properly via /api/demo-claim/{claim_id}."""
    for claim_id in ["CLM-001", "CLM-002", "CLM-003"]:
        response = client.get(f"/api/demo-claim/{claim_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["claim_id"] == claim_id
        assert len(data["documents"]) >= 1
        assert len(data["extracted_documents"]) >= 1
        assert len(data["all_facts"]) > 0
        assert data["primary_extraction"] is not None


def test_get_demo_claim_invalid_id():
    """Ensure invalid demo claim ID returns 404."""
    response = client.get("/api/demo-claim/CLM-999")
    assert response.status_code == 404


def test_demo_clm_001_full_pipeline_via_api():
    """Test full pipeline for CLM-001: clean accident claim -> READY_FOR_REVIEW."""
    demo_data = load_demo_claim("CLM-001")
    facts = demo_data["extracted_documents"]
    documents = demo_data["documents"]

    # Step 3: Retrieve Policy
    p_res = client.post("/api/retrieve-policy", json={"facts": facts, "claim_id": "CLM-001"})
    assert p_res.status_code == 200
    p_data = p_res.json()
    assert p_data["success"] is True
    assert len(p_data["clauses"]) >= 1

    # Step 4: Evaluate Rules
    r_res = client.post("/api/evaluate-policy", json={"facts": facts, "documents": documents, "claim_id": "CLM-001"})
    assert r_res.status_code == 200
    r_data = r_res.json()
    assert r_data["success"] is True
    assert r_data["summary"]["fail_count"] == 0

    # Step 5: Analyze Evidence
    e_res = client.post("/api/analyze-evidence", json={"facts": facts, "documents": documents, "claim_id": "CLM-001"})
    assert e_res.status_code == 200
    e_data = e_res.json()
    assert e_data["success"] is True
    assert len(e_data["contradictions"]) == 0
    assert e_data["summary"]["missing_evidence_count"] == 0

    # Step 6: Generate Review
    rev_res = client.post("/api/generate-review", json={"facts": facts, "documents": documents, "claim_id": "CLM-001"})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["success"] is True
    report = rev_data["report"]
    assert report["claim_type"] == "ACCIDENT"
    assert report["claim_summary"]["vehicle_registration"] == "TN01AB1234"
    assert report["claim_summary"]["vehicle_make_model"] == "Hyundai i20"
    assert report["claim_summary"]["incident_date"] == "2026-08-20"
    assert report["recommendation"]["status"] == "READY_FOR_REVIEW"


def test_demo_clm_002_full_pipeline_via_api():
    """Test full pipeline for CLM-002: contradiction claim -> REQUEST_INFORMATION."""
    demo_data = load_demo_claim("CLM-002")
    facts = demo_data["extracted_documents"]
    documents = demo_data["documents"]

    rev_res = client.post("/api/generate-review", json={"facts": facts, "documents": documents, "claim_id": "CLM-002"})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["success"] is True
    report = rev_data["report"]
    assert report["claim_type"] == "ACCIDENT"
    assert len(report["contradictions"]) >= 2
    assert report["recommendation"]["status"] == "REQUEST_INFORMATION"


def test_demo_clm_003_full_pipeline_via_api():
    """Test full pipeline for CLM-003: theft missing FIR -> REQUEST_INFORMATION."""
    demo_data = load_demo_claim("CLM-003")
    facts = demo_data["extracted_documents"]
    documents = demo_data["documents"]

    rev_res = client.post("/api/generate-review", json={"facts": facts, "documents": documents, "claim_id": "CLM-003"})
    assert rev_res.status_code == 200
    rev_data = rev_res.json()
    assert rev_data["success"] is True
    report = rev_data["report"]
    assert report["claim_type"] == "THEFT"
    missing = [c for c in report["completeness_findings"] if c["status"] == "MISSING"]
    assert len(missing) >= 1
    assert report["recommendation"]["status"] == "REQUEST_INFORMATION"
