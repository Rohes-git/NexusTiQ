"""Unit and integration tests for Milestone 1."""

import pytest
from fastapi.testclient import TestClient

from app import app
from src.config import Settings
from src.models import (
    Claim,
    ClaimFacts,
    Document,
    DocumentType,
    Evidence,
    Finding,
    FindingStatus,
    PolicyClause,
    Recommendation,
    ReviewResult,
)
from src.extraction.gemini_extractor import GeminiExtractor
from src.retrieval.embeddings import EmbeddingService
from src.retrieval.policy_retriever import PolicyRetriever
from src.rules.coverage import evaluate_coverage
from src.rules.documents import check_document_completeness
from src.rules.consistency import detect_contradictions
from src.rules.recommendation import compute_recommendation
from src.review.review_engine import ReviewEngine
from src.llm.report_writer import ReportWriter

client = TestClient(app)


# ── Health & Endpoint tests ──────────────────────────────────────────────

def test_health_endpoint():
    """GET /api/health must return status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_serve_frontend():
    """GET / must return HTML frontend."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "ClaimLens" in response.text
    assert "PS02" in response.text


def test_static_css_served():
    """GET /static/styles.css must return CSS."""
    response = client.get("/static/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")
    assert "ClaimLens" in response.text


def test_static_js_served():
    """GET /static/app.js must return JavaScript."""
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "ClaimLens" in response.text


def test_review_claim_endpoint():
    """POST /api/claims/review returns placeholder response."""
    response = client.post(
        "/api/claims/review",
        data={"incident_description": "Car hit tree", "claim_id": "CLM-001"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "received"
    assert "Review engine will be connected" in data["message"]
    assert data["claim_id"] == "CLM-001"
    assert data["incident_description_provided"] is True


# ── Config tests ──────────────────────────────────────────────────────────

def test_config_without_gemini_key():
    """Config loads cleanly when GEMINI_API_KEY is unset."""
    s = Settings()
    assert s.gemini_api_key == ""
    assert s.gemini_configured is False


# ── Model tests ───────────────────────────────────────────────────────────

def test_models_instantiation():
    """Domain models must instantiate without errors."""
    doc = Document(
        document_id="doc-1",
        document_type=DocumentType.CLAIM_FORM,
        filename="claim.pdf",
        text="Sample text",
        page_count=2,
    )
    assert doc.document_id == "doc-1"
    assert doc.document_type == DocumentType.CLAIM_FORM

    facts = ClaimFacts(
        vehicle_type="Car",
        vehicle_registration="KA01AB1234",
        claimed_amount=50000.0,
    )
    assert facts.claimed_amount == 50000.0

    evidence = Evidence(
        value="Front bumper damage",
        source_document="estimate.pdf",
        page=1,
        evidence_text="Replace front bumper",
        confidence=0.95,
    )
    assert evidence.confidence == 0.95

    finding = Finding(
        title="Valid Policy",
        status=FindingStatus.PASS,
        explanation="Policy was active on date of loss",
        evidence=[evidence],
    )
    assert finding.status == FindingStatus.PASS

    result = ReviewResult(
        recommendation=Recommendation.APPROVE,
        findings=[finding],
        contradictions=[],
        missing_information=[],
        escalation_required=False,
        summary="Claim is approved.",
    )
    assert result.recommendation == Recommendation.APPROVE


# ── Service placeholder tests ─────────────────────────────────────────────

def test_review_engine_placeholder():
    """ReviewEngine must return placeholder result without crashing."""
    engine = ReviewEngine()
    claim = Claim(claim_id="CLM-001", incident_description="Two-wheeler skid")
    result = engine.review(claim)
    assert isinstance(result, ReviewResult)
    assert result.recommendation == Recommendation.NEED_MORE_INFO


def test_placeholders_raise_not_implemented():
    """Unimplemented future milestone methods should raise NotImplementedError cleanly."""
    extractor = GeminiExtractor()
    with pytest.raises(NotImplementedError):
        extractor.extract_claim_facts(Document())

    with pytest.raises(NotImplementedError):
        detect_contradictions(ClaimFacts(), [])

    with pytest.raises(NotImplementedError):
        compute_recommendation([])

    writer = ReportWriter()
    with pytest.raises(NotImplementedError):
        writer.write_report(ReviewResult())
