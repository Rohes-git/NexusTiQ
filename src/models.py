"""Pydantic models for the ClaimLens domain.

These define the data structures the review pipeline will use.
Business logic is NOT implemented here — these are pure data containers.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────

class DocumentType(str, Enum):
    CLAIM_FORM = "claim_form"
    REPAIR_ESTIMATE = "repair_estimate"
    FIR = "fir"
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


# ── Core models ───────────────────────────────────────────────────────────

class Document(BaseModel):
    document_id: str = ""
    document_type: DocumentType = DocumentType.OTHER
    filename: str = ""
    text: str = ""
    page_count: int = 0


class ClaimFacts(BaseModel):
    """Structured facts extracted from claim documents."""
    vehicle_type: Optional[str] = None
    vehicle_registration: Optional[str] = None
    incident_date: Optional[str] = None
    incident_location: Optional[str] = None
    incident_description: Optional[str] = None
    claimed_amount: Optional[float] = None
    damage_description: Optional[str] = None
    policy_number: Optional[str] = None


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


class Claim(BaseModel):
    claim_id: str = ""
    documents: list[Document] = Field(default_factory=list)
    incident_description: str = ""
    facts: Optional[ClaimFacts] = None


class ClaimSubmission(BaseModel):
    """Incoming claim submission from the frontend."""
    claim_id: Optional[str] = None
    incident_description: str = ""
