"""Evidence Completeness Checker (Milestone 6).

Deterministically verifies submitted claim document inventory and required evidence
against canonical policy clauses (Clause 7.1 for Accident claims, Clause 7.2 & 3.2 for Theft claims).
Identifies PRESENT, MISSING, and INCOMPLETE evidence without LLM dependency.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from src.models import ExtractedFact, Document


class CompletenessStatus(str, Enum):
    PRESENT = "PRESENT"
    MISSING = "MISSING"
    INCOMPLETE = "INCOMPLETE"


class CompletenessFinding(BaseModel):
    """Auditable evidence requirement finding grounded in canonical policy clauses."""
    requirement_id: str = Field(..., description="Unique requirement identifier")
    clause_id: str = Field(..., description="Policy clause citation (e.g. '7.1', '7.2', '3.2')")
    required_document: str = Field(..., description="Human-readable required document or evidence item")
    status: CompletenessStatus = Field(..., description="PRESENT, MISSING, or INCOMPLETE")
    message: str = Field(..., description="Detailed explanation of the evidence requirement status")
    available_documents: list[str] = Field(default_factory=list, description="List of recognized submitted documents")
    evidence_details: Optional[str] = Field(None, description="Optional details or quotes from submitted evidence")


def determine_claim_type(
    facts: Union[dict[str, Any], list[Any], None] = None,
    documents: Optional[list[Any]] = None,
) -> str:
    """Deterministically determine claim type: 'ACCIDENT', 'THEFT', or 'UNKNOWN'.

    Checks:
    1. 'incident_type' / 'claim_type' in extracted facts
    2. Keywords in 'incident_description'
    3. Distinctive document types (e.g. FIR without accident context)
    """
    facts_dict: dict[str, Any] = {}
    if facts is None:
        facts_dict = {}
    elif isinstance(facts, dict):
        facts_dict = facts
    elif isinstance(facts, list):
        for item in facts:
            if isinstance(item, ExtractedFact):
                facts_dict[item.field_name] = item.value
            elif isinstance(item, dict):
                if "field_name" in item:
                    facts_dict[item["field_name"]] = item.get("value")
                elif "facts" in item:
                    sub_facts = item["facts"]
                    if isinstance(sub_facts, list):
                        for sf in sub_facts:
                            if isinstance(sf, ExtractedFact):
                                facts_dict[sf.field_name] = sf.value
                            elif isinstance(sf, dict):
                                facts_dict[sf.get("field_name", "")] = sf.get("value")
                    elif isinstance(sub_facts, dict):
                        for k, v in sub_facts.items():
                            facts_dict[k] = v.value if isinstance(v, ExtractedFact) else (v.get("value") if isinstance(v, dict) else v)
                for k in ["incident_type", "claim_type", "incident_description"]:
                    if k in item and item[k]:
                        facts_dict[k] = item[k]
    else:
        facts_dict = {}

    # 1. Direct fact lookup
    type_val = facts_dict.get("incident_type") or facts_dict.get("claim_type")
    if type_val:
        type_str = str(type_val).lower().strip()
        if any(w in type_str for w in ["theft", "stolen", "burglary", "missing"]):
            return "THEFT"
        if any(w in type_str for w in ["accident", "collision", "crash", "damage", "repair", "overturn", "skid"]):
            return "ACCIDENT"

    # 2. Description keyword analysis
    desc = facts_dict.get("incident_description")
    if not desc and isinstance(facts_dict.get("claim_form"), dict):
        desc = facts_dict["claim_form"].get("incident_description")
    if desc:
        desc_str = str(desc).lower().strip()
        theft_keywords = ["theft", "stolen", "burglary", "housebreaking", "missing overnight", "vehicle was stolen", "not recovered"]
        accident_keywords = ["accident", "collision", "collided", "impact", "bumper", "dent", "damage", "repair", "hit", "skid"]

        is_theft = any(k in desc_str for k in theft_keywords)
        is_accident = any(k in desc_str for k in accident_keywords)

        if is_theft and not is_accident:
            return "THEFT"
        if is_accident and not is_theft:
            return "ACCIDENT"

    # 3. Document inventory clues
    if documents:
        doc_names = [str(d).lower() for d in documents]
        has_estimate = any("estimate" in d or "repair" in d for d in doc_names)
        has_fir = any("fir" in d or "police" in d for d in doc_names)

        if has_estimate and not has_fir:
            return "ACCIDENT"
        if has_fir and not has_estimate:
            return "THEFT"

    return "UNKNOWN"


class CompletenessChecker:
    """Deterministic evidence completeness checker against policy clauses 7.1 and 7.2."""

    def __init__(self):
        pass

    @staticmethod
    def _normalize_doc_inventory(
        documents: Optional[list[Any]],
        facts: Union[dict[str, Any], list[Any], None],
    ) -> tuple[list[str], bool, bool, bool, bool]:
        """Classify available documents and evidence presence.

        Returns:
            (doc_names, has_claim_form, has_repair_estimate, has_fir, has_incident_desc)
        """
        doc_names: list[str] = []
        has_claim_form = False
        has_repair_estimate = False
        has_fir = False
        has_incident_desc = False

        if documents:
            for d in documents:
                if isinstance(d, Document):
                    name = d.filename or d.document_type.value
                elif isinstance(d, dict):
                    name = d.get("filename") or d.get("document_type") or "Document"
                else:
                    name = str(d)
                doc_names.append(name)

                name_lower = name.lower()
                if any(w in name_lower for w in ["claim_form", "claim form", "claim-form"]):
                    has_claim_form = True
                elif any(w in name_lower for w in ["repair", "estimate", "repair_estimate"]):
                    has_repair_estimate = True
                elif any(w in name_lower for w in ["fir", "police"]):
                    has_fir = True

        # Check facts for presence of specific document data
        if isinstance(facts, dict):
            if "claim_form" in facts:
                has_claim_form = True
            if "repair_estimate" in facts:
                has_repair_estimate = True
            if "fir" in facts:
                has_fir = True
            if "repair_estimate_amount" in facts and facts["repair_estimate_amount"] is not None:
                has_repair_estimate = True
            if facts.get("incident_description") or (isinstance(facts.get("claim_form"), dict) and facts["claim_form"].get("incident_description")):
                has_incident_desc = True

        elif isinstance(facts, list):
            for item in facts:
                if isinstance(item, ExtractedFact):
                    if item.field_name in ["claim_id", "policy_number"]:
                        has_claim_form = True
                    elif item.field_name == "repair_estimate_amount":
                        has_repair_estimate = True
                    elif item.field_name == "incident_description" and item.value:
                        has_incident_desc = True
                elif isinstance(item, dict):
                    doc_t = str(item.get("document_type", "")).lower()
                    doc_n = str(item.get("document_name", item.get("filename", ""))).lower()
                    if "claim" in doc_t or "claim" in doc_n:
                        has_claim_form = True
                    if "repair" in doc_t or "estimate" in doc_t or "repair" in doc_n or "estimate" in doc_n:
                        has_repair_estimate = True
                    if "fir" in doc_t or "police" in doc_t or "fir" in doc_n or "police" in doc_n:
                        has_fir = True

                    sub_facts = item.get("facts", [])
                    if isinstance(sub_facts, list):
                        for sf in sub_facts:
                            fn = sf.field_name if isinstance(sf, ExtractedFact) else sf.get("field_name")
                            val = sf.value if isinstance(sf, ExtractedFact) else sf.get("value")
                            if fn == "repair_estimate_amount" and val is not None:
                                has_repair_estimate = True
                            if fn == "incident_description" and val:
                                has_incident_desc = True
                    elif isinstance(sub_facts, dict):
                        if "repair_estimate_amount" in sub_facts:
                            has_repair_estimate = True
                        if sub_facts.get("incident_description"):
                            has_incident_desc = True

        return doc_names, has_claim_form, has_repair_estimate, has_fir, has_incident_desc

    def check(
        self,
        facts: Union[dict[str, Any], list[ExtractedFact], None] = None,
        documents: Optional[list[Any]] = None,
    ) -> list[CompletenessFinding]:
        """Evaluate evidence completeness against canonical policy requirements.

        Returns:
            List of CompletenessFinding objects.
        """
        claim_type = determine_claim_type(facts, documents)
        doc_names, has_cf, has_re, has_fir, has_desc = self._normalize_doc_inventory(documents, facts)

        findings: list[CompletenessFinding] = []

        if claim_type == "ACCIDENT":
            # Clause 7.1 Requirements for Accidental Damage
            # 1. Claim Form
            if has_cf:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.1-CLAIM-FORM",
                    clause_id="7.1",
                    required_document="Claim Form",
                    status=CompletenessStatus.PRESENT,
                    message="Completed Claim Form is submitted and available.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.1-CLAIM-FORM",
                    clause_id="7.1",
                    required_document="Claim Form",
                    status=CompletenessStatus.MISSING,
                    message="Accidental damage claim requires a completed Claim Form under Clause 7.1, but none was provided.",
                    available_documents=doc_names,
                ))

            # 2. Repair Estimate (Clause 7.1 & 2.2)
            if has_re:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.1-REPAIR-ESTIMATE",
                    clause_id="7.1",
                    required_document="Repair Estimate",
                    status=CompletenessStatus.PRESENT,
                    message="Itemized Repair Estimate is submitted and available.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.1-REPAIR-ESTIMATE",
                    clause_id="7.1",
                    required_document="Repair Estimate",
                    status=CompletenessStatus.MISSING,
                    message="Accidental damage claim requires an itemized Repair Estimate under Clause 7.1 and Clause 2.2, but none was provided.",
                    available_documents=doc_names,
                ))

            # 3. Incident Description (Clause 7.1)
            if has_desc:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.1-INCIDENT-DESC",
                    clause_id="7.1",
                    required_document="Incident Description",
                    status=CompletenessStatus.PRESENT,
                    message="Clear description of incident circumstances is provided.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.1-INCIDENT-DESC",
                    clause_id="7.1",
                    required_document="Incident Description",
                    status=CompletenessStatus.MISSING,
                    message="Accidental damage claim requires a clear description of incident circumstances under Clause 7.1, but none was provided.",
                    available_documents=doc_names,
                ))

        elif claim_type == "THEFT":
            # Clause 7.2 Requirements for Theft Claims
            # 1. Claim Form
            if has_cf:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.2-CLAIM-FORM",
                    clause_id="7.2",
                    required_document="Claim Form",
                    status=CompletenessStatus.PRESENT,
                    message="Completed Claim Form is submitted and available.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.2-CLAIM-FORM",
                    clause_id="7.2",
                    required_document="Claim Form",
                    status=CompletenessStatus.MISSING,
                    message="Theft claim requires a completed Claim Form under Clause 7.2, but none was provided.",
                    available_documents=doc_names,
                ))

            # 2. FIR (First Information Report) (Clause 7.2 & 3.2)
            if has_fir:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.2-FIR",
                    clause_id="7.2",
                    required_document="FIR",
                    status=CompletenessStatus.PRESENT,
                    message="First Information Report (FIR) is submitted and available.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.2-FIR",
                    clause_id="7.2",
                    required_document="FIR",
                    status=CompletenessStatus.MISSING,
                    message="Theft claim requires a mandatory First Information Report (FIR) under Clause 3.2 and Clause 7.2, but no FIR document was provided.",
                    available_documents=doc_names,
                ))

            # 3. Incident Description / Loss Statement (Clause 7.2)
            if has_desc:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.2-INCIDENT-DESC",
                    clause_id="7.2",
                    required_document="Incident Description",
                    status=CompletenessStatus.PRESENT,
                    message="Detailed statement of loss circumstances is provided.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-7.2-INCIDENT-DESC",
                    clause_id="7.2",
                    required_document="Incident Description",
                    status=CompletenessStatus.MISSING,
                    message="Theft claim requires a detailed statement of loss circumstances under Clause 7.2, but none was provided.",
                    available_documents=doc_names,
                ))

        else:
            # UNKNOWN claim type: Check general minimum claim documentation
            findings.append(CompletenessFinding(
                requirement_id="REQ-UNKNOWN-TYPE",
                clause_id="7.1",
                required_document="Claim Type Determination",
                status=CompletenessStatus.INCOMPLETE,
                message="Claim type (Accident vs Theft) could not be determined. Please provide incident details to verify required document checklist.",
                available_documents=doc_names,
            ))

            if has_cf:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-GEN-CLAIM-FORM",
                    clause_id="7.1",
                    required_document="Claim Form",
                    status=CompletenessStatus.PRESENT,
                    message="Completed Claim Form is submitted.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-GEN-CLAIM-FORM",
                    clause_id="7.1",
                    required_document="Claim Form",
                    status=CompletenessStatus.MISSING,
                    message="Claim requires a completed Claim Form, but none was provided.",
                    available_documents=doc_names,
                ))

            if has_desc:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-GEN-INCIDENT-DESC",
                    clause_id="7.1",
                    required_document="Incident Description",
                    status=CompletenessStatus.PRESENT,
                    message="Detailed incident description is provided.",
                    available_documents=doc_names,
                ))
            else:
                findings.append(CompletenessFinding(
                    requirement_id="REQ-GEN-INCIDENT-DESC",
                    clause_id="7.1",
                    required_document="Incident Description",
                    status=CompletenessStatus.MISSING,
                    message="Claim requires an incident description detailing the loss circumstances, but none was provided.",
                    available_documents=doc_names,
                ))

        return findings
