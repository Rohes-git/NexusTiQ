"""Deterministic Cross-Document Contradiction Detector (Milestone 6).

Compares extracted facts across claim documents (Claim Form, Repair Estimate, FIR)
using deterministic Python comparison and normalization rules without LLM dependency.
Preserves full evidence provenance (source document, page number, exact quote).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from src.models import ExtractedFact, normalize_amount, normalize_date


# ── Controlled Enums ──────────────────────────────────────────────────────

class ContradictionCategory(str, Enum):
    INCIDENT_DATE_MISMATCH = "INCIDENT_DATE_MISMATCH"
    CLAIM_AMOUNT_MISMATCH = "CLAIM_AMOUNT_MISMATCH"
    VEHICLE_REGISTRATION_MISMATCH = "VEHICLE_REGISTRATION_MISMATCH"
    VEHICLE_DETAILS_MISMATCH = "VEHICLE_DETAILS_MISMATCH"
    NOTIFICATION_DATE_MISMATCH = "NOTIFICATION_DATE_MISMATCH"
    CLAIM_TYPE_MISMATCH = "CLAIM_TYPE_MISMATCH"
    OTHER_MATERIAL_CONTRADICTION = "OTHER_MATERIAL_CONTRADICTION"


class ContradictionSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Data Models ───────────────────────────────────────────────────────────

class ContradictionFinding(BaseModel):
    """Auditable cross-document contradiction finding with full evidence provenance."""
    contradiction_id: str = Field(..., description="Unique identifier for the contradiction")
    category: ContradictionCategory = Field(..., description="Standardized contradiction category")
    severity: ContradictionSeverity = Field(..., description="Severity of the contradiction (HIGH/MEDIUM/LOW)")
    field_name: str = Field(..., description="Name of the conflicting fact field")
    document_a: str = Field(..., description="Name or type of the first document")
    document_b: str = Field(..., description="Name or type of the second document")
    value_a: Any = Field(None, description="Normalized value from Document A")
    value_b: Any = Field(None, description="Normalized value from Document B")
    raw_value_a: Optional[str] = Field(None, description="Raw displayed value from Document A")
    raw_value_b: Optional[str] = Field(None, description="Raw displayed value from Document B")
    evidence_a: str = Field("", description="Exact short quote from Document A")
    evidence_b: str = Field("", description="Exact short quote from Document B")
    page_a: Optional[int] = Field(1, description="1-indexed page number in Document A")
    page_b: Optional[int] = Field(1, description="1-indexed page number in Document B")
    message: str = Field(..., description="Clear explanation of the detected discrepancy")
    status: str = Field("CONTRADICTION", description="Finding status")


class ConsistentFieldFinding(BaseModel):
    """Record of a verified consistent field across multiple documents."""
    field_name: str
    category: str
    document_a: str
    document_b: str
    value: Any
    message: str

    @property
    def documents(self) -> list[str]:
        return [self.document_a, self.document_b]


class DocumentFactRecord(BaseModel):
    """Container for facts associated with a specific document."""
    document_name: str
    document_type: str = "unknown"
    facts: dict[str, ExtractedFact] = Field(default_factory=dict)

    def __init__(self, **data: Any):
        facts_dict = dict(data.get("facts", {}))
        known_fields = [
            "incident_date", "notification_date", "claimed_amount",
            "repair_estimate_amount", "vehicle_registration", "vehicle_make",
            "vehicle_model", "incident_type", "incident_description", "policy_number"
        ]
        for field in known_fields:
            if field in data and data[field] is not None:
                val = data[field]
                raw_val = data.get(f"raw_{field}", str(val))
                ev = data.get(f"{field}_evidence", str(val))
                pg = data.get(f"{field}_page", 1)
                facts_dict[field] = ExtractedFact(
                    field_name=field,
                    value=val,
                    raw_value=str(raw_val) if raw_val is not None else None,
                    evidence_text=str(ev) if ev is not None else "",
                    page_number=int(pg) if pg is not None else 1,
                )
        data["facts"] = facts_dict
        super().__init__(**data)


# ── Normalization Helpers ────────────────────────────────────────────────

def normalize_reg_number(reg_str: Optional[str]) -> Optional[str]:
    """Normalize vehicle registration numbers (remove spaces, hyphens, uppercase)."""
    if not reg_str:
        return None
    cleaned = re.sub(r"[^A-Z0-9]", "", str(reg_str).upper())
    return cleaned if cleaned else None


def normalize_string_value(text: Optional[str]) -> Optional[str]:
    """Normalize general string fields (whitespace collapse, lowercased)."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", str(text)).strip().lower()
    return cleaned if cleaned else None


# ── Contradiction Detector Class ─────────────────────────────────────────

class ContradictionDetector:
    """Deterministic cross-document contradiction detector for motor claims."""

    @staticmethod
    def _extract_doc_records(
        facts: Union[dict[str, Any], list[ExtractedFact], list[dict[str, Any]], None],
        documents: Optional[list[Any]] = None,
    ) -> list[DocumentFactRecord]:
        """Convert varied input structures into normalized per-document fact records."""
        records: list[DocumentFactRecord] = []

        if facts is None:
            return records

        # Case 1: Dictionary with per-document sub-dictionaries (e.g. metadata.json format)
        if isinstance(facts, dict):
            # Check for explicit document keys like "claim_form", "repair_estimate", "fir"
            has_doc_subdicts = any(
                k in facts and isinstance(facts[k], dict)
                for k in ["claim_form", "repair_estimate", "fir", "police_fir"]
            )

            if has_doc_subdicts:
                if "claim_form" in facts and isinstance(facts["claim_form"], dict):
                    cf_facts = {}
                    for k, v in facts["claim_form"].items():
                        cf_facts[k] = ExtractedFact(
                            field_name=k,
                            value=v,
                            raw_value=str(v),
                            evidence_text=str(v),
                            page_number=1,
                        )
                    # Inherit top-level facts if not in subdict
                    for top_k in ["vehicle_registration", "vehicle_make", "vehicle_model", "incident_type", "policy_number"]:
                        if top_k in facts and top_k not in cf_facts and facts[top_k] is not None:
                            cf_facts[top_k] = ExtractedFact(
                                field_name=top_k,
                                value=facts[top_k],
                                raw_value=str(facts[top_k]),
                                evidence_text=str(facts[top_k]),
                                page_number=1,
                            )
                    records.append(DocumentFactRecord(
                        document_name="Claim Form",
                        document_type="claim_form",
                        facts=cf_facts,
                    ))

                if "repair_estimate" in facts and isinstance(facts["repair_estimate"], dict):
                    re_facts = {}
                    for k, v in facts["repair_estimate"].items():
                        # Map estimated_repair_amount -> repair_estimate_amount / claimed_amount
                        field_k = "repair_estimate_amount" if k in ["estimated_repair_amount", "amount", "total_amount"] else k
                        re_facts[field_k] = ExtractedFact(
                            field_name=field_k,
                            value=v,
                            raw_value=str(v),
                            evidence_text=str(v),
                            page_number=1,
                        )
                    # Inherit top-level facts if not in subdict
                    for top_k in ["vehicle_registration", "vehicle_make", "vehicle_model"]:
                        if top_k in facts and top_k not in re_facts and facts[top_k] is not None:
                            re_facts[top_k] = ExtractedFact(
                                field_name=top_k,
                                value=facts[top_k],
                                raw_value=str(facts[top_k]),
                                evidence_text=str(facts[top_k]),
                                page_number=1,
                            )
                    records.append(DocumentFactRecord(
                        document_name="Repair Estimate",
                        document_type="repair_estimate",
                        facts=re_facts,
                    ))

                if "fir" in facts and isinstance(facts["fir"], dict):
                    fir_facts = {}
                    for k, v in facts["fir"].items():
                        fir_facts[k] = ExtractedFact(
                            field_name=k,
                            value=v,
                            raw_value=str(v),
                            evidence_text=str(v),
                            page_number=1,
                        )
                    records.append(DocumentFactRecord(
                        document_name="FIR",
                        document_type="fir",
                        facts=fir_facts,
                    ))

                return records

            # Flat dict of facts containing both claimed_amount and repair_estimate_amount
            # or multiple document items
            flat_facts: dict[str, ExtractedFact] = {}
            for k, v in facts.items():
                if isinstance(v, ExtractedFact):
                    flat_facts[k] = v
                elif isinstance(v, dict) and "value" in v:
                    flat_facts[k] = ExtractedFact(
                        field_name=k,
                        value=v.get("value"),
                        raw_value=str(v.get("raw_value", v.get("value", ""))),
                        evidence_text=str(v.get("evidence_text", "")),
                        page_number=v.get("page_number", 1),
                    )
                else:
                    flat_facts[k] = ExtractedFact(
                        field_name=k,
                        value=v,
                        raw_value=str(v) if v is not None else None,
                        evidence_text=str(v) if v is not None else "",
                        page_number=1,
                    )

            # If both claimed_amount and repair_estimate_amount exist, construct virtual doc records
            cf_dict = {}
            re_dict = {}
            for k, ef in flat_facts.items():
                if k == "claimed_amount":
                    cf_dict[k] = ef
                elif k == "repair_estimate_amount":
                    re_dict[k] = ef
                else:
                    cf_dict[k] = ef
                    re_dict[k] = ef

            if "repair_estimate_amount" in flat_facts and "claimed_amount" in flat_facts:
                records.append(DocumentFactRecord(
                    document_name="Claim Form",
                    document_type="claim_form",
                    facts=cf_dict,
                ))
                records.append(DocumentFactRecord(
                    document_name="Repair Estimate",
                    document_type="repair_estimate",
                    facts=re_dict,
                ))
                return records

            records.append(DocumentFactRecord(
                document_name="Claim Submission",
                document_type="claim_form",
                facts=flat_facts,
            ))
            return records

        # Case 2: List of ExtractedFact objects
        if isinstance(facts, list):
            # Check if elements are ExtractedFact or document bundles
            if facts and isinstance(facts[0], ExtractedFact):
                flat_facts_map: dict[str, ExtractedFact] = {f.field_name: f for f in facts}

                if "claimed_amount" in flat_facts_map and "repair_estimate_amount" in flat_facts_map:
                    cf_map = {k: f for k, f in flat_facts_map.items() if k != "repair_estimate_amount"}
                    re_map = {k: f for k, f in flat_facts_map.items() if k != "claimed_amount"}
                    records.append(DocumentFactRecord(
                        document_name="Claim Form",
                        document_type="claim_form",
                        facts=cf_map,
                    ))
                    records.append(DocumentFactRecord(
                        document_name="Repair Estimate",
                        document_type="repair_estimate",
                        facts=re_map,
                    ))
                else:
                    records.append(DocumentFactRecord(
                        document_name="Submitted Document",
                        document_type="unknown",
                        facts=flat_facts_map,
                    ))
                return records

            # Check if elements are document bundle dicts
            for item in facts:
                if isinstance(item, dict):
                    doc_name = item.get("filename") or item.get("document_name") or item.get("document_type") or "Document"
                    doc_type = item.get("document_type", "unknown")
                    item_facts = item.get("facts", {})
                    fact_map = {}
                    if isinstance(item_facts, list):
                        for f in item_facts:
                            if isinstance(f, ExtractedFact):
                                fact_map[f.field_name] = f
                            elif isinstance(f, dict):
                                fn = f.get("field_name", "unknown")
                                fact_map[fn] = ExtractedFact(
                                    field_name=fn,
                                    value=f.get("value"),
                                    raw_value=str(f.get("raw_value", f.get("value", ""))),
                                    evidence_text=str(f.get("evidence_text", "")),
                                    page_number=f.get("page_number", 1),
                                )
                    elif isinstance(item_facts, dict):
                        for k, v in item_facts.items():
                            if isinstance(v, ExtractedFact):
                                fact_map[k] = v
                            else:
                                fact_map[k] = ExtractedFact(
                                    field_name=k,
                                    value=v,
                                    raw_value=str(v),
                                    evidence_text=str(v),
                                    page_number=1,
                                )
                    records.append(DocumentFactRecord(
                        document_name=doc_name,
                        document_type=doc_type,
                        facts=fact_map,
                    ))

        return records

    def compare_records(
        self,
        doc_records: list[DocumentFactRecord],
    ) -> tuple[list[ContradictionFinding], list[ConsistentFieldFinding]]:
        """Perform pairwise comparison on an explicit list of DocumentFactRecords."""
        contradictions: list[ContradictionFinding] = []
        consistent_fields: list[ConsistentFieldFinding] = []

        if len(doc_records) < 2:
            return contradictions, consistent_fields

        # Compare each pair of documents
        for i in range(len(doc_records)):
            for j in range(i + 1, len(doc_records)):
                rec_a = doc_records[i]
                rec_b = doc_records[j]

                # 1. Incident Date Comparison
                self._compare_incident_date(rec_a, rec_b, contradictions, consistent_fields)

                # 2. Claim Amount vs Repair Estimate Comparison
                self._compare_amounts(rec_a, rec_b, contradictions, consistent_fields)

                # 3. Vehicle Registration Comparison
                self._compare_vehicle_registration(rec_a, rec_b, contradictions, consistent_fields)

                # 4. Vehicle Make & Model Comparison
                self._compare_vehicle_details(rec_a, rec_b, contradictions, consistent_fields)

                # 5. Notification Date Comparison
                self._compare_notification_date(rec_a, rec_b, contradictions, consistent_fields)

                # 6. Incident / Claim Type Comparison
                self._compare_incident_type(rec_a, rec_b, contradictions, consistent_fields)

        return contradictions, consistent_fields

    def detect(
        self,
        facts: Union[dict[str, Any], list[ExtractedFact], list[dict[str, Any]], None],
        documents: Optional[list[Any]] = None,
    ) -> tuple[list[ContradictionFinding], list[ConsistentFieldFinding]]:
        """Perform deterministic cross-document contradiction checks.

        Returns:
            Tuple of (list of ContradictionFinding, list of ConsistentFieldFinding).
        """
        doc_records = self._extract_doc_records(facts, documents)
        return self.compare_records(doc_records)

    def _compare_incident_date(
        self,
        doc_a: DocumentFactRecord,
        doc_b: DocumentFactRecord,
        contradictions: list[ContradictionFinding],
        consistent_fields: list[ConsistentFieldFinding],
    ) -> None:
        """Compare incident dates across documents."""
        fact_a = doc_a.facts.get("incident_date")
        fact_b = doc_b.facts.get("incident_date")

        # Missing in one or both documents -> NOT a contradiction
        if not fact_a or not fact_b or fact_a.value is None or fact_b.value is None:
            return

        norm_a = normalize_date(str(fact_a.value)) or normalize_date(str(fact_a.raw_value))
        norm_b = normalize_date(str(fact_b.value)) or normalize_date(str(fact_b.raw_value))

        if not norm_a or not norm_b:
            return

        if norm_a != norm_b:
            raw_a = fact_a.raw_value or str(fact_a.value)
            raw_b = fact_b.raw_value or str(fact_b.value)
            contradictions.append(ContradictionFinding(
                contradiction_id=f"CONT-DATE-{len(contradictions) + 1:03d}",
                category=ContradictionCategory.INCIDENT_DATE_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="incident_date",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value_a=norm_a,
                value_b=norm_b,
                raw_value_a=raw_a,
                raw_value_b=raw_b,
                evidence_a=fact_a.evidence_text or raw_a,
                evidence_b=fact_b.evidence_text or raw_b,
                page_a=fact_a.page_number,
                page_b=fact_b.page_number,
                message=(
                    f"Incident date mismatch between {doc_a.document_name} ({raw_a}) "
                    f"and {doc_b.document_name} ({raw_b})."
                ),
            ))
        else:
            consistent_fields.append(ConsistentFieldFinding(
                field_name="incident_date",
                category="INCIDENT_DATE",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value=norm_a,
                message=f"Incident date ({norm_a}) is consistent across {doc_a.document_name} and {doc_b.document_name}.",
            ))

    def _compare_amounts(
        self,
        doc_a: DocumentFactRecord,
        doc_b: DocumentFactRecord,
        contradictions: list[ContradictionFinding],
        consistent_fields: list[ConsistentFieldFinding],
    ) -> None:
        """Compare claimed amount vs repair estimate amount / financial figures."""
        # Find amounts in doc_a and doc_b
        # Doc A might have claimed_amount or repair_estimate_amount
        amt_fact_a = (
            doc_a.facts.get("claimed_amount")
            or doc_a.facts.get("repair_estimate_amount")
            or doc_a.facts.get("estimated_repair_amount")
            or doc_a.facts.get("amount")
        )
        amt_fact_b = (
            doc_b.facts.get("repair_estimate_amount")
            or doc_b.facts.get("claimed_amount")
            or doc_b.facts.get("estimated_repair_amount")
            or doc_b.facts.get("amount")
        )

        if not amt_fact_a or not amt_fact_b or amt_fact_a.value is None or amt_fact_b.value is None:
            return

        norm_a = normalize_amount(str(amt_fact_a.value)) or normalize_amount(str(amt_fact_a.raw_value))
        norm_b = normalize_amount(str(amt_fact_b.value)) or normalize_amount(str(amt_fact_b.raw_value))

        if norm_a is None or norm_b is None:
            return

        diff = abs(norm_a - norm_b)
        if diff >= 1.0:
            raw_a = amt_fact_a.raw_value or f"₹{norm_a:,.2f}"
            raw_b = amt_fact_b.raw_value or f"₹{norm_b:,.2f}"
            contradictions.append(ContradictionFinding(
                contradiction_id=f"CONT-AMOUNT-{len(contradictions) + 1:03d}",
                category=ContradictionCategory.CLAIM_AMOUNT_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="claimed_amount_vs_repair_estimate",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value_a=norm_a,
                value_b=norm_b,
                raw_value_a=raw_a,
                raw_value_b=raw_b,
                evidence_a=amt_fact_a.evidence_text or raw_a,
                evidence_b=amt_fact_b.evidence_text or raw_b,
                page_a=amt_fact_a.page_number,
                page_b=amt_fact_b.page_number,
                message=(
                    f"Financial mismatch between claimed amount in {doc_a.document_name} ({raw_a}) "
                    f"and estimated repair cost in {doc_b.document_name} ({raw_b}) "
                    f"(Discrepancy: ₹{diff:,.2f})."
                ),
            ))
        else:
            consistent_fields.append(ConsistentFieldFinding(
                field_name="claimed_amount",
                category="FINANCIAL",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value=norm_a,
                message=f"Financial amount (₹{norm_a:,.0f}) is consistent across {doc_a.document_name} and {doc_b.document_name}.",
            ))

    def _compare_vehicle_registration(
        self,
        doc_a: DocumentFactRecord,
        doc_b: DocumentFactRecord,
        contradictions: list[ContradictionFinding],
        consistent_fields: list[ConsistentFieldFinding],
    ) -> None:
        """Compare vehicle registration numbers across documents."""
        fact_a = doc_a.facts.get("vehicle_registration")
        fact_b = doc_b.facts.get("vehicle_registration")

        if not fact_a or not fact_b or fact_a.value is None or fact_b.value is None:
            return

        norm_a = normalize_reg_number(str(fact_a.value)) or normalize_reg_number(str(fact_a.raw_value))
        norm_b = normalize_reg_number(str(fact_b.value)) or normalize_reg_number(str(fact_b.raw_value))

        if not norm_a or not norm_b:
            return

        if norm_a != norm_b:
            raw_a = fact_a.raw_value or str(fact_a.value)
            raw_b = fact_b.raw_value or str(fact_b.value)
            contradictions.append(ContradictionFinding(
                contradiction_id=f"CONT-REG-{len(contradictions) + 1:03d}",
                category=ContradictionCategory.VEHICLE_REGISTRATION_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="vehicle_registration",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value_a=norm_a,
                value_b=norm_b,
                raw_value_a=raw_a,
                raw_value_b=raw_b,
                evidence_a=fact_a.evidence_text or raw_a,
                evidence_b=fact_b.evidence_text or raw_b,
                page_a=fact_a.page_number,
                page_b=fact_b.page_number,
                message=(
                    f"Vehicle registration mismatch between {doc_a.document_name} ({raw_a}) "
                    f"and {doc_b.document_name} ({raw_b})."
                ),
            ))
        else:
            consistent_fields.append(ConsistentFieldFinding(
                field_name="vehicle_registration",
                category="VEHICLE_IDENTIFICATION",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value=norm_a,
                message=f"Vehicle registration ({norm_a}) is consistent across {doc_a.document_name} and {doc_b.document_name}.",
            ))

    def _compare_vehicle_details(
        self,
        doc_a: DocumentFactRecord,
        doc_b: DocumentFactRecord,
        contradictions: list[ContradictionFinding],
        consistent_fields: list[ConsistentFieldFinding],
    ) -> None:
        """Compare vehicle make / model across documents."""
        for field in ["vehicle_make", "vehicle_model"]:
            fact_a = doc_a.facts.get(field)
            fact_b = doc_b.facts.get(field)

            if not fact_a or not fact_b or fact_a.value is None or fact_b.value is None:
                continue

            norm_a = normalize_string_value(str(fact_a.value))
            norm_b = normalize_string_value(str(fact_b.value))

            if not norm_a or not norm_b:
                continue

            if norm_a != norm_b:
                raw_a = fact_a.raw_value or str(fact_a.value)
                raw_b = fact_b.raw_value or str(fact_b.value)
                contradictions.append(ContradictionFinding(
                    contradiction_id=f"CONT-VEH-{len(contradictions) + 1:03d}",
                    category=ContradictionCategory.VEHICLE_DETAILS_MISMATCH,
                    severity=ContradictionSeverity.MEDIUM,
                    field_name=field,
                    document_a=doc_a.document_name,
                    document_b=doc_b.document_name,
                    value_a=norm_a,
                    value_b=norm_b,
                    raw_value_a=raw_a,
                    raw_value_b=raw_b,
                    evidence_a=fact_a.evidence_text or raw_a,
                    evidence_b=fact_b.evidence_text or raw_b,
                    page_a=fact_a.page_number,
                    page_b=fact_b.page_number,
                    message=(
                        f"Vehicle {field.replace('_', ' ')} mismatch between {doc_a.document_name} ({raw_a}) "
                        f"and {doc_b.document_name} ({raw_b})."
                    ),
                ))
            else:
                consistent_fields.append(ConsistentFieldFinding(
                    field_name=field,
                    category="VEHICLE_IDENTIFICATION",
                    document_a=doc_a.document_name,
                    document_b=doc_b.document_name,
                    value=norm_a,
                    message=f"{field.replace('_', ' ').title()} ({norm_a.title()}) is consistent.",
                ))

    def _compare_notification_date(
        self,
        doc_a: DocumentFactRecord,
        doc_b: DocumentFactRecord,
        contradictions: list[ContradictionFinding],
        consistent_fields: list[ConsistentFieldFinding],
    ) -> None:
        """Compare notification dates across documents if present in both."""
        fact_a = doc_a.facts.get("notification_date")
        fact_b = doc_b.facts.get("notification_date")

        if not fact_a or not fact_b or fact_a.value is None or fact_b.value is None:
            return

        norm_a = normalize_date(str(fact_a.value)) or normalize_date(str(fact_a.raw_value))
        norm_b = normalize_date(str(fact_b.value)) or normalize_date(str(fact_b.raw_value))

        if not norm_a or not norm_b:
            return

        if norm_a != norm_b:
            raw_a = fact_a.raw_value or str(fact_a.value)
            raw_b = fact_b.raw_value or str(fact_b.value)
            contradictions.append(ContradictionFinding(
                contradiction_id=f"CONT-NOTIF-{len(contradictions) + 1:03d}",
                category=ContradictionCategory.NOTIFICATION_DATE_MISMATCH,
                severity=ContradictionSeverity.MEDIUM,
                field_name="notification_date",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value_a=norm_a,
                value_b=norm_b,
                raw_value_a=raw_a,
                raw_value_b=raw_b,
                evidence_a=fact_a.evidence_text or raw_a,
                evidence_b=fact_b.evidence_text or raw_b,
                page_a=fact_a.page_number,
                page_b=fact_b.page_number,
                message=(
                    f"Notification date mismatch between {doc_a.document_name} ({raw_a}) "
                    f"and {doc_b.document_name} ({raw_b})."
                ),
            ))
        else:
            consistent_fields.append(ConsistentFieldFinding(
                field_name="notification_date",
                category="TIMELINE",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value=norm_a,
                message=f"Notification date ({norm_a}) is consistent across documents.",
            ))

    def _compare_incident_type(
        self,
        doc_a: DocumentFactRecord,
        doc_b: DocumentFactRecord,
        contradictions: list[ContradictionFinding],
        consistent_fields: list[ConsistentFieldFinding],
    ) -> None:
        """Compare incident or claim type across documents if present in both."""
        fact_a = doc_a.facts.get("incident_type") or doc_a.facts.get("claim_type")
        fact_b = doc_b.facts.get("incident_type") or doc_b.facts.get("claim_type")

        if not fact_a or not fact_b or fact_a.value is None or fact_b.value is None:
            return

        norm_a = normalize_string_value(str(fact_a.value))
        norm_b = normalize_string_value(str(fact_b.value))

        if not norm_a or not norm_b:
            return

        if norm_a != norm_b:
            raw_a = fact_a.raw_value or str(fact_a.value)
            raw_b = fact_b.raw_value or str(fact_b.value)
            contradictions.append(ContradictionFinding(
                contradiction_id=f"CONT-TYPE-{len(contradictions) + 1:03d}",
                category=ContradictionCategory.CLAIM_TYPE_MISMATCH,
                severity=ContradictionSeverity.HIGH,
                field_name="incident_type",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value_a=norm_a,
                value_b=norm_b,
                raw_value_a=raw_a,
                raw_value_b=raw_b,
                evidence_a=fact_a.evidence_text or raw_a,
                evidence_b=fact_b.evidence_text or raw_b,
                page_a=fact_a.page_number,
                page_b=fact_b.page_number,
                message=(
                    f"Claim / incident type mismatch between {doc_a.document_name} ({raw_a}) "
                    f"and {doc_b.document_name} ({raw_b})."
                ),
            ))
        else:
            consistent_fields.append(ConsistentFieldFinding(
                field_name="incident_type",
                category="CLAIM_TYPE",
                document_a=doc_a.document_name,
                document_b=doc_b.document_name,
                value=norm_a,
                message=f"Claim type ({norm_a.title()}) is consistent across documents.",
            ))
