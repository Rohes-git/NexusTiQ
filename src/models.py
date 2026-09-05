"""Pydantic models for the ClaimLens domain and extraction pipeline.

Defines data containers for:
- Page-aware document representations
- Structured fact extraction schemas
- Evidence validation and normalization
- Downstream claim review domain objects
"""

from __future__ import annotations

import re
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    CLAIM_FORM = "claim_form"
    REPAIR_ESTIMATE = "repair_estimate"
    FIR = "fir"
    UNKNOWN = "unknown"
    PHOTO = "photo"
    OTHER = "other"


class FindingStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"
    MISSING = "missing"


class Recommendation(str, Enum):
    APPROVE = "approve"
    DENY = "deny"
    ESCALATE = "escalate"
    NEED_MORE_INFO = "need_more_info"
    REQUEST_INFORMATION = "request_information"


# ── Document text & Page models ──────────────────────────────────────────

class DocumentPage(BaseModel):
    """Represents text extracted from a single page of a PDF."""
    page_number: int = Field(..., description="1-indexed page number")
    text: str = Field(..., description="Raw text extracted from this page")


class DocumentText(BaseModel):
    """Page-aware structured text extracted from a document."""
    filename: str = ""
    document_type: DocumentType = DocumentType.UNKNOWN
    pages: list[DocumentPage] = Field(default_factory=list)
    total_pages: int = 0

    def get_full_text(self) -> str:
        """Concatenate text from all pages."""
        return "\n\n".join(page.text for page in self.pages)

    def get_page_aware_text(self) -> str:
        """Format text with explicit page markers for LLM ingestion."""
        parts = []
        for page in self.pages:
            parts.append(f"--- PAGE {page.page_number} ---\n{page.text.strip()}")
        return "\n\n".join(parts)

    def get_page_text(self, page_number: int) -> Optional[str]:
        """Get text of a specific 1-indexed page."""
        for page in self.pages:
            if page.page_number == page_number:
                return page.text
        return None


# ── Extracted Fact & Evidence models ─────────────────────────────────────

class ExtractedFact(BaseModel):
    """A single fact extracted from a document with traceable provenance."""
    field_name: str = Field(..., description="Name of the extracted field")
    value: Optional[Any] = Field(None, description="Normalized value")
    raw_value: Optional[str] = Field(None, description="Raw value string as stated in document")
    evidence_text: str = Field("", description="Exact short quote from document text")
    page_number: int = Field(1, description="1-indexed page number containing the evidence")
    confidence: float = Field(1.0, ge=0.0, le=1.0, description="Confidence score")
    evidence_valid: bool = Field(True, description="True if evidence text verified in source page")


class RawFactItem(BaseModel):
    """Schema for individual facts returned by Gemini structured output."""
    raw_value: Optional[str] = Field(None, description="Value as extracted from document, or null if absent")
    evidence_text: Optional[str] = Field(None, description="Exact short quote from the document supporting this fact")
    page_number: Optional[int] = Field(None, description="1-indexed page number where evidence appears")
    confidence: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Confidence score 0.0 to 1.0")


class GeminiExtractionSchema(BaseModel):
    """Pydantic schema used for Gemini structured output."""
    document_type: str = Field(
        ...,
        description="Classified document type: 'claim_form', 'repair_estimate', 'fir', or 'unknown'"
    )
    claim_id: Optional[RawFactItem] = None
    policy_number: Optional[RawFactItem] = None
    vehicle_registration: Optional[RawFactItem] = None
    vehicle_make: Optional[RawFactItem] = None
    vehicle_model: Optional[RawFactItem] = None
    incident_type: Optional[RawFactItem] = None
    incident_date: Optional[RawFactItem] = None
    notification_date: Optional[RawFactItem] = None
    incident_description: Optional[RawFactItem] = None
    claimed_amount: Optional[RawFactItem] = None
    repair_estimate_amount: Optional[RawFactItem] = None


class DocumentSummary(BaseModel):
    """Summary of the ingested document."""
    filename: str
    document_type: str
    page_count: int


class ExtractionError(BaseModel):
    """Structured error information."""
    code: str
    message: str


class ExtractionResponse(BaseModel):
    """API response for /api/extract-document."""
    success: bool
    document: Optional[DocumentSummary] = None
    facts: list[ExtractedFact] = Field(default_factory=list)
    error: Optional[ExtractionError] = None


# ── Domain models ─────────────────────────────────────────────────────────

class Evidence(BaseModel):
    value: str = ""
    source_document: str = ""
    page: int = 0
    evidence_text: str = ""
    confidence: float = 0.0


class PolicyClause(BaseModel):
    clause_id: str = ""
    title: str = ""
    description: str = ""
    applicable: bool = False


class Finding(BaseModel):
    title: str = ""
    status: FindingStatus = FindingStatus.MISSING
    explanation: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    policy_clause: Optional[PolicyClause] = None


class ReviewResult(BaseModel):
    recommendation: Recommendation = Recommendation.NEED_MORE_INFO
    findings: list[Finding] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    escalation_required: bool = False
    summary: str = ""


class Document(BaseModel):
    document_id: str = ""
    document_type: DocumentType = DocumentType.OTHER
    filename: str = ""
    text: str = ""
    page_count: int = 0


class ClaimFacts(BaseModel):
    vehicle_type: Optional[str] = None
    vehicle_registration: Optional[str] = None
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None
    incident_description: Optional[str] = None
    claimed_amount: Optional[float] = None
    damage_description: Optional[str] = None
    policy_number: Optional[str] = None


class Claim(BaseModel):
    claim_id: str = ""
    documents: list[Document] = Field(default_factory=list)
    incident_description: str = ""
    facts: Optional[ClaimFacts] = None


class ClaimSubmission(BaseModel):
    claim_id: Optional[str] = None
    incident_description: str = ""


# ── Normalization Helpers ────────────────────────────────────────────────

def normalize_amount(raw_str: Optional[str]) -> Optional[float]:
    """Extract and normalize numerical currency amounts.

    Examples:
        '₹78,000' -> 78000.0
        '85,000.00' -> 85000.0
        '92000' -> 92000.0
        'Rs. 72,000/-' -> 72000.0
    """
    if not raw_str:
        return None

    cleaned = str(raw_str).strip()
    # Remove words like Rs, INR, and optional trailing periods
    cleaned = re.sub(r"(?i)\b(rs|inr)\b\.?", "", cleaned)
    # Remove trailing /- or /
    cleaned = re.sub(r"/[-\s]*$", "", cleaned)
    # Extract only digits, commas, and periods
    cleaned = re.sub(r"[^\d.,]", "", cleaned).strip()
    if not cleaned:
        return None

    # Remove commas
    cleaned = cleaned.replace(",", "")
    # If multiple dots, keep last one as decimal
    if cleaned.count(".") > 1:
        parts = cleaned.split(".")
        cleaned = "".join(parts[:-1]) + "." + parts[-1]

    try:
        val = float(cleaned)
        return int(val) if val.is_integer() else val
    except ValueError:
        return None


def normalize_date(raw_str: Optional[str]) -> Optional[str]:
    """Normalize date strings to ISO YYYY-MM-DD format.

    Supports:
        '20 August 2026', '20 Aug 2026', '20/08/2026', '2026-08-20', '20-08-2026'
    """
    if not raw_str:
        return None

    raw_clean = str(raw_str).strip()

    # Direct ISO match
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw_clean):
        return raw_clean

    formats = [
        "%d %B %Y",      # 20 August 2026
        "%d %b %Y",      # 20 Aug 2026
        "%d/%m/%Y",      # 20/08/2026
        "%d-%m-%Y",      # 20-08-2026
        "%Y/%m/%d",      # 2026/08/20
        "%B %d, %Y",     # August 20, 2026
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(raw_clean, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # If no standard format matched, return clean string as-is
    return raw_clean
