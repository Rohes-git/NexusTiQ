"""Unit tests for Milestone 3 Document Ingestion and Fact Extraction."""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app import app
from src.extraction.document_loader import (
    DocumentLoader,
    EmptyDocumentError,
    InvalidFileTypeError,
    CorruptedDocumentError,
)
from src.extraction.gemini_extractor import (
    GeminiExtractor,
    verify_evidence_in_page,
)
from src.models import (
    DocumentPage,
    DocumentText,
    DocumentType,
    ExtractedFact,
    GeminiExtractionSchema,
    normalize_amount,
    normalize_date,
)

BASE_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = BASE_DIR / "tests" / "fixtures"
DEMO_DIR = BASE_DIR / "data" / "demo_claims"

client = TestClient(app)


# ── 1. Document Loader Tests ──────────────────────────────────────────────

def test_load_valid_demo_pdf():
    """Test loading valid PDF preserves pages and text."""
    pdf_path = DEMO_DIR / "claim_001_clean_accident" / "claim_form.pdf"
    doc_text = DocumentLoader.load_pdf(pdf_path)

    assert isinstance(doc_text, DocumentText)
    assert doc_text.filename == "claim_form.pdf"
    assert doc_text.total_pages >= 1
    assert len(doc_text.pages) == doc_text.total_pages

    page_1 = doc_text.pages[0]
    assert page_1.page_number == 1
    assert "MOTOR INSURANCE CLAIM FORM" in page_1.text
    assert "CLM-001" in page_1.text


def test_load_pdf_from_bytes():
    """Test loading PDF directly from raw bytes."""
    pdf_path = DEMO_DIR / "claim_001_clean_accident" / "claim_form.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    doc_text = DocumentLoader.load_pdf(pdf_bytes, filename="uploaded_claim.pdf")
    assert doc_text.filename == "uploaded_claim.pdf"
    assert "CLM-001" in doc_text.get_full_text()


def test_load_non_pdf_file_raises_error(tmp_path):
    """Test non-PDF file raises InvalidFileTypeError."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("This is plain text.")

    with pytest.raises(InvalidFileTypeError):
        DocumentLoader.load_pdf(txt_file)


def test_load_invalid_bytes_signature():
    """Test bytes without %PDF header raise InvalidFileTypeError."""
    with pytest.raises(InvalidFileTypeError):
        DocumentLoader.load_pdf(b"NOT A REAL PDF FILE")


def test_load_nonexistent_file():
    """Test missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        DocumentLoader.load_pdf("nonexistent_path/fake.pdf")


def test_corrupt_pdf_handling(tmp_path):
    """Test corrupt PDF data raises CorruptedDocumentError."""
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_bytes(b"%PDF-1.4\ncorrupted content that cannot parse")

    with pytest.raises(CorruptedDocumentError):
        DocumentLoader.load_pdf(corrupt_pdf)


# ── 2. Normalization Tests ────────────────────────────────────────────────

def test_amount_normalization():
    """Test numerical amount extraction and normalization."""
    assert normalize_amount("₹78,000") == 78000
    assert normalize_amount("85,000.00") == 85000
    assert normalize_amount("92000") == 92000
    assert normalize_amount("Rs. 72,000/-") == 72000
    assert normalize_amount("INR 1,50,000") == 150000
    assert normalize_amount("Total: ₹1,50,000") == 150000
    assert normalize_amount(None) is None
    assert normalize_amount("") is None
    assert normalize_amount("abc") is None


def test_date_normalization():
    """Test date parsing and conversion to ISO format."""
    assert normalize_date("20 August 2026") == "2026-08-20"
    assert normalize_date("20 Aug 2026") == "2026-08-20"
    assert normalize_date("20/08/2026") == "2026-08-20"
    assert normalize_date("20-08-2026") == "2026-08-20"
    assert normalize_date("August 20, 2026") == "2026-08-20"
    assert normalize_date("2026-08-20") == "2026-08-20"
    assert normalize_date(None) is None
    assert normalize_date("") is None


# ── 3. Evidence Validation Tests ──────────────────────────────────────────

def test_evidence_verification_exact_and_normalized():
    """Test verify_evidence_in_page handles spacing and case."""
    page_text = "Incident Date: 20 August 2026\nVehicle: Hyundai i20\nTotal: ₹78,000"

    # Exact match
    assert verify_evidence_in_page("Incident Date: 20 August 2026", page_text) is True

    # Whitespace tolerant
    assert verify_evidence_in_page("Incident   Date:   20   August 2026", page_text) is True

    # Case insensitive
    assert verify_evidence_in_page("incident date: 20 august 2026", page_text) is True

    # Hallucinated / Non-existent evidence must fail
    assert verify_evidence_in_page("Driver was intoxicated", page_text) is False
    assert verify_evidence_in_page("Incident Date: 15 July 2025", page_text) is False
    assert verify_evidence_in_page("", page_text) is False
    assert verify_evidence_in_page("text", "") is False


# ── 4. Mocked Gemini Schema Processing using Fixtures ──────────────────────

def test_process_clean_claim_form_fixture():
    """Test fact processing and evidence verification on CLM-001 claim form."""
    pdf_path = DEMO_DIR / "claim_001_clean_accident" / "claim_form.pdf"
    doc_text = DocumentLoader.load_pdf(pdf_path)

    fixture_path = FIXTURES_DIR / "clean_claim_form_extraction.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    raw_schema = GeminiExtractionSchema.model_validate(schema_data)
    extractor = GeminiExtractor(api_key="mocked_key")

    doc_type, facts = extractor.process_raw_schema(raw_schema, doc_text)

    assert doc_type == DocumentType.CLAIM_FORM
    assert len(facts) >= 8

    fact_dict = {f.field_name: f for f in facts}
    assert fact_dict["claim_id"].value == "CLM-001"
    assert fact_dict["policy_number"].value == "POL-001"
    assert fact_dict["claimed_amount"].value == 78000
    assert fact_dict["incident_date"].value == "2026-08-20"

    # Every fact in this clean fixture must have valid verified evidence
    for fact in facts:
        assert fact.evidence_valid is True, f"Fact {fact.field_name} evidence should be valid"


def test_process_repair_estimate_fixture():
    """Test fact processing on CLM-001 repair estimate."""
    pdf_path = DEMO_DIR / "claim_001_clean_accident" / "repair_estimate.pdf"
    doc_text = DocumentLoader.load_pdf(pdf_path)

    fixture_path = FIXTURES_DIR / "repair_estimate_extraction.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        schema_data = json.load(f)

    raw_schema = GeminiExtractionSchema.model_validate(schema_data)
    extractor = GeminiExtractor(api_key="mocked_key")

    doc_type, facts = extractor.process_raw_schema(raw_schema, doc_text)

    assert doc_type == DocumentType.REPAIR_ESTIMATE
    fact_dict = {f.field_name: f for f in facts}
    assert fact_dict["repair_estimate_amount"].value == 78000
    assert fact_dict["repair_estimate_amount"].evidence_valid is True


def test_hallucinated_evidence_marked_invalid():
    """Test that a fabricated citation quote is flagged as evidence_valid = False."""
    doc_text = DocumentText(
        filename="test.pdf",
        total_pages=1,
        pages=[DocumentPage(page_number=1, text="Simple incident on road with car TN01AB1234")],
    )

    schema_data = {
        "document_type": "claim_form",
        "incident_date": {
            "raw_value": "15 August 2026",
            "evidence_text": "Fabricated text not in document",
            "page_number": 1,
            "confidence": 0.9,
        }
    }
    raw_schema = GeminiExtractionSchema.model_validate(schema_data)
    extractor = GeminiExtractor(api_key="mocked_key")

    _, facts = extractor.process_raw_schema(raw_schema, doc_text)

    assert len(facts) == 1
    assert facts[0].field_name == "incident_date"
    assert facts[0].evidence_valid is False  # Must be invalid!


# ── 5. API Endpoint Tests ─────────────────────────────────────────────────

def test_extract_endpoint_unsupported_extension():
    """POST /api/extract-document with .txt file returns unsupported type error."""
    files = {"file": ("test.txt", b"some content", "text/plain")}
    response = client.post("/api/extract-document", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_extract_endpoint_without_gemini_key_returns_graceful_error(monkeypatch):
    """POST /api/extract-document with valid PDF but no API key returns GEMINI_UNAVAILABLE."""
    from src.config import Settings
    import app as app_module

    # Mock settings as unconfigured
    unconfigured_settings = Settings(gemini_api_key="")
    monkeypatch.setattr(app_module, "settings", unconfigured_settings)

    pdf_path = DEMO_DIR / "claim_001_clean_accident" / "claim_form.pdf"
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    files = {"file": ("claim_form.pdf", pdf_bytes, "application/pdf")}
    response = client.post("/api/extract-document", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "GEMINI_UNAVAILABLE"
    assert "GEMINI_API_KEY" in data["error"]["message"]
