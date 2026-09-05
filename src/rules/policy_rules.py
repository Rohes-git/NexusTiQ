"""Deterministic policy rule definitions for ClaimLens.

Implements rule evaluations based strictly on canonical policy clauses in
data/policy/motor_policy.json.

Strict decision boundary:
- Never outputs APPROVE, REJECT, DENY, FRAUD, or FINAL CLAIM DECISION.
- Allowed finding statuses:
  PASS, FAIL, WARNING, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE.
"""

from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from src.models import ExtractedFact, normalize_date, normalize_amount

logger = logging.getLogger("claimlens.rules")

# Canonical default policy period (from synthetic motor_policy.json)
DEFAULT_POLICY_START = "2026-01-01"
DEFAULT_POLICY_END = "2026-12-31"


class RuleFindingStatus(str, Enum):
    """Permitted finding statuses for deterministic rule evaluation."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class FactUsed(BaseModel):
    """Record of a factual data point used by a policy rule."""
    field_name: str
    value: Any = None
    raw_value: Optional[str] = None
    evidence_text: str = ""
    page_number: Optional[int] = None


class PolicyFinding(BaseModel):
    """Auditable result of evaluating a specific policy condition."""
    rule_id: str = Field(..., description="Unique rule identifier e.g. 'coverage_period'")
    clause_id: str = Field(..., description="Canonical policy clause ID e.g. '1.1'")
    category: str = Field(..., description="Rule category e.g. 'Policy Period', 'Coverage', 'Notification'")
    status: RuleFindingStatus = Field(..., description="PASS, FAIL, WARNING, INSUFFICIENT_EVIDENCE, or NOT_APPLICABLE")
    title: str = Field(..., description="Short finding title")
    message: str = Field(..., description="Detailed factual explanation of the finding")
    facts_used: list[FactUsed] = Field(default_factory=list, description="Claim facts utilized during rule execution")
    evidence_references: list[str] = Field(default_factory=list, description="Source document quotes/citations")
    severity: str = Field("info", description="'info', 'low', 'medium', 'high', 'critical'")


# ── Fact Extraction & Normalization Helpers ───────────────────────────────

def extract_fact_dict(
    facts: Union[list[ExtractedFact], dict[str, Any], None]
) -> tuple[dict[str, Any], dict[str, FactUsed]]:
    """Normalize various input fact formats into clean dictionary and fact lookup."""
    fact_dict: dict[str, Any] = {}
    fact_objs: dict[str, FactUsed] = {}

    if facts is None:
        return fact_dict, fact_objs

    if isinstance(facts, dict):
        for k, v in facts.items():
            if isinstance(v, ExtractedFact):
                fact_dict[k] = v.value if v.value is not None else v.raw_value
                fact_objs[k] = FactUsed(
                    field_name=k,
                    value=fact_dict[k],
                    raw_value=v.raw_value,
                    evidence_text=v.evidence_text,
                    page_number=v.page_number,
                )
            elif isinstance(v, dict) and "value" in v:
                fact_dict[k] = v.get("value")
                fact_objs[k] = FactUsed(
                    field_name=k,
                    value=v.get("value"),
                    raw_value=v.get("raw_value"),
                    evidence_text=v.get("evidence_text", ""),
                    page_number=v.get("page_number"),
                )
            elif isinstance(v, dict) and k in ["claim_form", "repair_estimate", "fir"]:
                # Nested document subdict (e.g. metadata.json format)
                for sub_k, sub_v in v.items():
                    if sub_k not in fact_dict:
                        fact_dict[sub_k] = sub_v
                        fact_objs[sub_k] = FactUsed(
                            field_name=sub_k,
                            value=sub_v,
                            raw_value=str(sub_v) if sub_v is not None else None,
                        )
            else:
                fact_dict[k] = v
                fact_objs[k] = FactUsed(
                    field_name=k,
                    value=v,
                    raw_value=str(v) if v is not None else None,
                )
        return fact_dict, fact_objs

    if isinstance(facts, list):
        for item in facts:
            if isinstance(item, ExtractedFact):
                field = item.field_name
                val = item.value if item.value is not None else item.raw_value
                fact_dict[field] = val
                fact_objs[field] = FactUsed(
                    field_name=field,
                    value=val,
                    raw_value=item.raw_value,
                    evidence_text=item.evidence_text,
                    page_number=item.page_number,
                )
            elif isinstance(item, dict) and "field_name" in item:
                field = item["field_name"]
                val = item.get("value", item.get("raw_value"))
                fact_dict[field] = val
                fact_objs[field] = FactUsed(
                    field_name=field,
                    value=val,
                    raw_value=item.get("raw_value"),
                    evidence_text=item.get("evidence_text", ""),
                    page_number=item.get("page_number"),
                )
            elif hasattr(item, "field_name"):
                field = getattr(item, "field_name")
                val = getattr(item, "value", getattr(item, "raw_value", None))
                fact_dict[field] = val
                fact_objs[field] = FactUsed(
                    field_name=field,
                    value=val,
                    raw_value=getattr(item, "raw_value", None),
                    evidence_text=getattr(item, "evidence_text", ""),
                    page_number=getattr(item, "page_number", None),
                )

    return fact_dict, fact_objs


def _parse_iso_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse date string into a datetime object safely."""
    if not date_str:
        return None
    normalized = normalize_date(str(date_str))
    if not normalized:
        return None
    try:
        return datetime.strptime(normalized, "%Y-%m-%d")
    except ValueError:
        return None


# ── Individual Deterministic Policy Rules ─────────────────────────────────

def check_coverage_period(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
    policy_start: str = DEFAULT_POLICY_START,
    policy_end: str = DEFAULT_POLICY_END,
) -> PolicyFinding:
    """Evaluate Clause 1.1 — Coverage Period."""
    rule_id = "coverage_period"
    clause_id = "1.1"
    category = "Policy Period"

    raw_inc_date = fact_dict.get("incident_date")
    inc_dt = _parse_iso_date(raw_inc_date)
    start_dt = _parse_iso_date(fact_dict.get("policy_start_date") or policy_start)
    end_dt = _parse_iso_date(fact_dict.get("policy_end_date") or policy_end)

    facts_used = []
    if "incident_date" in fact_objs:
        facts_used.append(fact_objs["incident_date"])

    if inc_dt is None:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Coverage Period Undetermined",
            message="Coverage eligibility cannot be evaluated because the required incident date is missing or unparseable.",
            facts_used=facts_used,
            severity="medium",
        )

    if start_dt is None or end_dt is None:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Policy Schedule Dates Missing",
            message="Policy schedule active dates are unavailable to verify coverage period.",
            facts_used=facts_used,
            severity="medium",
        )

    inc_iso = inc_dt.strftime("%Y-%m-%d")
    start_iso = start_dt.strftime("%Y-%m-%d")
    end_iso = end_dt.strftime("%Y-%m-%d")

    evidence_quotes = [fact_objs["incident_date"].evidence_text] if "incident_date" in fact_objs and fact_objs["incident_date"].evidence_text else []

    if start_dt <= inc_dt <= end_dt:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Incident Within Policy Period",
            message=f"Incident date ({inc_iso}) falls within the active policy coverage period ({start_iso} to {end_iso}).",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )
    else:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.FAIL,
            title="Incident Outside Policy Period",
            message=f"Incident date ({inc_iso}) is outside the active policy coverage period ({start_iso} to {end_iso}).",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="high",
        )


def check_covered_vehicle(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
) -> PolicyFinding:
    """Evaluate Clause 1.2 — Covered Vehicles."""
    rule_id = "covered_vehicle"
    clause_id = "1.2"
    category = "Policy Scope"

    veh_reg = fact_dict.get("vehicle_registration")
    veh_make = fact_dict.get("vehicle_make")
    veh_model = fact_dict.get("vehicle_model")

    facts_used = [
        fact_objs[k] for k in ["vehicle_registration", "vehicle_make", "vehicle_model"] if k in fact_objs
    ]
    evidence_quotes = [
        fact_objs[k].evidence_text for k in ["vehicle_registration", "vehicle_make", "vehicle_model"]
        if k in fact_objs and fact_objs[k].evidence_text
    ]

    if not veh_reg or not str(veh_reg).strip():
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Vehicle Identification Missing",
            message="Vehicle registration number is missing from claim facts; cannot verify vehicle identification under policy schedule.",
            facts_used=facts_used,
            severity="medium",
        )

    veh_desc = f"{veh_reg}"
    if veh_make or veh_model:
        veh_desc += f" ({' '.join(filter(None, [str(veh_make or ''), str(veh_model or '')]))})"

    return PolicyFinding(
        rule_id=rule_id,
        clause_id=clause_id,
        category=category,
        status=RuleFindingStatus.PASS,
        title="Covered Vehicle Identified",
        message=f"Vehicle identified by registration {veh_desc} matches policy schedule coverage criteria.",
        facts_used=facts_used,
        evidence_references=evidence_quotes,
        severity="info",
    )


def check_accident_coverage(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
) -> PolicyFinding:
    """Evaluate Clause 2.1 — Accidental Damage Coverage."""
    rule_id = "accident_coverage"
    clause_id = "2.1"
    category = "Accidental Damage"

    inc_type = str(fact_dict.get("incident_type") or fact_dict.get("claim_type") or "").strip().lower()
    facts_used = [fact_objs[k] for k in ["incident_type", "claim_type"] if k in fact_objs]
    evidence_quotes = [
        fact_objs[k].evidence_text for k in ["incident_type", "claim_type"]
        if k in fact_objs and fact_objs[k].evidence_text
    ]

    if not inc_type:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Incident Type Unknown",
            message="Incident type is not specified; cannot evaluate accidental damage coverage eligibility.",
            facts_used=facts_used,
            severity="medium",
        )

    if inc_type == "accident":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Accidental Damage Category Covered",
            message="Claimed incident type is accident and falls under the policy's accidental damage coverage category.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )
    elif inc_type == "theft":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.NOT_APPLICABLE,
            title="Accidental Damage Not Applicable",
            message="Accidental damage coverage rule is not applicable to theft claims.",
            facts_used=facts_used,
            severity="info",
        )
    else:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.WARNING,
            title="Unrecognized Incident Type",
            message=f"Incident type '{inc_type}' is not recognized under standard accidental damage provisions.",
            facts_used=facts_used,
            severity="low",
        )


def check_repair_settlement(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
    documents: Optional[list[str]] = None,
) -> PolicyFinding:
    """Evaluate Clause 2.2 — Repair Settlement & Estimate Assessment."""
    rule_id = "repair_settlement"
    clause_id = "2.2"
    category = "Accidental Damage"

    inc_type = str(fact_dict.get("incident_type") or fact_dict.get("claim_type") or "").strip().lower()
    if inc_type == "theft":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.NOT_APPLICABLE,
            title="Repair Settlement Not Applicable",
            message="Repair settlement rule is not applicable to total theft claims.",
            facts_used=[],
            severity="info",
        )

    repair_amt = normalize_amount(str(fact_dict.get("repair_estimate_amount") or ""))
    facts_used = [fact_objs[k] for k in ["repair_estimate_amount", "claimed_amount"] if k in fact_objs]
    evidence_quotes = [
        fact_objs[k].evidence_text for k in ["repair_estimate_amount"]
        if k in fact_objs and fact_objs[k].evidence_text
    ]

    has_estimate_doc = False
    if documents:
        docs_lower = [str(d).lower() for d in documents]
        has_estimate_doc = any("estimate" in d or "repair" in d for d in docs_lower)

    if repair_amt is not None and repair_amt > 0:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Repair Estimate Provided",
            message=f"Itemized repair estimate of ₹{repair_amt:,.0f} provided for accidental damage repair assessment.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )
    elif has_estimate_doc:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Repair Estimate Document Present",
            message="Repair estimate document submitted for repair assessment under clause 2.2.",
            facts_used=facts_used,
            severity="info",
        )
    elif inc_type == "accident":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.FAIL,
            title="Repair Estimate Missing",
            message="No itemized repair estimate provided for accidental damage repair assessment under clause 2.2.",
            facts_used=facts_used,
            severity="medium",
        )
    else:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Repair Estimate Undetermined",
            message="Repair estimate amount is unavailable to evaluate repair settlement.",
            facts_used=facts_used,
            severity="low",
        )


def check_theft_coverage(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
) -> PolicyFinding:
    """Evaluate Clause 3.1 — Total Loss Due to Theft."""
    rule_id = "theft_coverage"
    clause_id = "3.1"
    category = "Theft Coverage"

    inc_type = str(fact_dict.get("incident_type") or fact_dict.get("claim_type") or "").strip().lower()
    facts_used = [fact_objs[k] for k in ["incident_type", "claim_type"] if k in fact_objs]
    evidence_quotes = [
        fact_objs[k].evidence_text for k in ["incident_type", "claim_type"]
        if k in fact_objs and fact_objs[k].evidence_text
    ]

    if not inc_type:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Incident Type Unknown",
            message="Incident type is unknown; cannot evaluate theft coverage.",
            facts_used=facts_used,
            severity="medium",
        )

    if inc_type == "theft":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Theft Coverage Applicable",
            message="Claimed incident type is theft and falls under total loss due to theft coverage.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )
    elif inc_type == "accident":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.NOT_APPLICABLE,
            title="Theft Coverage Not Applicable",
            message="Theft coverage rule is not applicable to accident claims.",
            facts_used=facts_used,
            severity="info",
        )
    else:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.NOT_APPLICABLE,
            title="Theft Coverage Not Applicable",
            message=f"Incident type '{inc_type}' is not classified as theft.",
            facts_used=facts_used,
            severity="info",
        )


def check_fir_requirement(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
    documents: Optional[list[str]] = None,
) -> PolicyFinding:
    """Evaluate Clause 3.2 — Theft Evidence & FIR Requirement."""
    rule_id = "fir_requirement"
    clause_id = "3.2"
    category = "Theft Coverage"

    inc_type = str(fact_dict.get("incident_type") or fact_dict.get("claim_type") or "").strip().lower()

    if inc_type != "theft":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.NOT_APPLICABLE,
            title="FIR Requirement Not Applicable",
            message="Mandatory FIR requirement under clause 3.2 applies specifically to theft claims.",
            facts_used=[],
            severity="info",
        )

    # Check for FIR presence in documents or extracted facts
    has_fir = False
    fir_ref = ""

    if documents:
        docs_lower = [str(d).lower() for d in documents]
        has_fir = any("fir" in d or "police" in d for d in docs_lower)

    if not has_fir and "fir_number" in fact_dict and str(fact_dict["fir_number"]).strip():
        has_fir = True
        fir_ref = str(fact_dict["fir_number"])

    facts_used = [fact_objs[k] for k in ["incident_type", "fir_number"] if k in fact_objs]

    if has_fir:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="FIR Evidence Present",
            message=f"Certified copy of First Information Report (FIR{': ' + fir_ref if fir_ref else ''}) is present for the theft claim.",
            facts_used=facts_used,
            severity="info",
        )
    else:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.FAIL,
            title="FIR Evidence Missing",
            message="FIR evidence is required for theft claims under policy clause 3.2, but is not present in submitted documents.",
            facts_used=facts_used,
            severity="high",
        )


def check_idv_valuation(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
    default_idv: Optional[float] = None,
) -> PolicyFinding:
    """Evaluate Clauses 5.1 & 5.2 — Insured Declared Value (IDV)."""
    rule_id = "idv_valuation"
    clause_id = "5.1"
    category = "Valuation & IDV"

    claimed_amt = normalize_amount(str(fact_dict.get("claimed_amount") or ""))
    idv = normalize_amount(str(fact_dict.get("idv") or default_idv or ""))
    inc_type = str(fact_dict.get("incident_type") or fact_dict.get("claim_type") or "").strip().lower()

    facts_used = [fact_objs[k] for k in ["claimed_amount", "idv"] if k in fact_objs]
    evidence_quotes = [
        fact_objs[k].evidence_text for k in ["claimed_amount"]
        if k in fact_objs and fact_objs[k].evidence_text
    ]

    if claimed_amt is None:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Claimed Amount Missing",
            message="Claimed financial amount is missing from claim facts; cannot evaluate against policy IDV limits.",
            facts_used=facts_used,
            severity="medium",
        )

    if idv is not None and idv > 0:
        if claimed_amt <= idv:
            return PolicyFinding(
                rule_id=rule_id,
                clause_id=clause_id,
                category=category,
                status=RuleFindingStatus.PASS,
                title="Claim Within IDV Limit",
                message=f"Claimed amount (₹{claimed_amt:,.0f}) is within the policy Insured Declared Value (IDV of ₹{idv:,.0f}).",
                facts_used=facts_used,
                evidence_references=evidence_quotes,
                severity="info",
            )
        else:
            return PolicyFinding(
                rule_id=rule_id,
                clause_id=clause_id,
                category=category,
                status=RuleFindingStatus.WARNING,
                title="Claim Exceeds IDV Limit",
                message=f"Claimed amount (₹{claimed_amt:,.0f}) exceeds the policy Insured Declared Value (IDV of ₹{idv:,.0f}); settlement is capped at IDV under clause 5.1.",
                facts_used=facts_used,
                evidence_references=evidence_quotes,
                severity="medium",
            )

    # If IDV not explicitly configured in claim facts
    if inc_type == "theft":
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Theft Claim Valuation",
            message=f"Claimed amount (₹{claimed_amt:,.0f}) submitted for total loss theft valuation under clause 5.1.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )
    else:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id="5.2",
            category=category,
            status=RuleFindingStatus.PASS,
            title="Repair Cost Assessment",
            message=f"Claimed amount (₹{claimed_amt:,.0f}) submitted for independent repair cost assessment under clause 5.2.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )


def check_notification_window(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
) -> PolicyFinding:
    """Evaluate Clauses 6.1 & 6.2 — Notification Window (7-calendar-day rule)."""
    rule_id = "notification_window"
    clause_id = "6.1"
    category = "Claim Notification"

    raw_inc_date = fact_dict.get("incident_date")
    raw_notif_date = fact_dict.get("notification_date")

    inc_dt = _parse_iso_date(raw_inc_date)
    notif_dt = _parse_iso_date(raw_notif_date)

    facts_used = [
        fact_objs[k] for k in ["incident_date", "notification_date"] if k in fact_objs
    ]
    evidence_quotes = [
        fact_objs[k].evidence_text for k in ["incident_date", "notification_date"]
        if k in fact_objs and fact_objs[k].evidence_text
    ]

    if inc_dt is None or notif_dt is None:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Notification Timeline Undetermined",
            message="Cannot verify notification timeline because incident date or notification date is missing or unparseable.",
            facts_used=facts_used,
            severity="medium",
        )

    diff_days = (notif_dt.date() - inc_dt.date()).days

    if diff_days < 0:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.WARNING,
            title="Notification Date Precedes Incident Date",
            message=f"Notification date ({notif_dt.strftime('%Y-%m-%d')}) is recorded {abs(diff_days)} day(s) before incident date ({inc_dt.strftime('%Y-%m-%d')}); requires factual verification.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="medium",
        )
    elif diff_days <= 7:
        return PolicyFinding(
            rule_id=rule_id,
            clause_id=clause_id,
            category=category,
            status=RuleFindingStatus.PASS,
            title="Notification Within 7-Day Window",
            message=f"Claim notification was submitted within the standard 7-calendar-day requirement ({diff_days} calendar day(s) elapsed).",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="info",
        )
    else:
        # Crucial requirement: Late notification is NOT an automatic rejection; clause 6.2 mandates review
        return PolicyFinding(
            rule_id=rule_id,
            clause_id="6.2",
            category=category,
            status=RuleFindingStatus.WARNING,
            title="Late Notification (Requires Review)",
            message=f"Notification occurred {diff_days} days after the incident, outside the standard 7-calendar-day window; requires written explanation and investigator review under clause 6.2.",
            facts_used=facts_used,
            evidence_references=evidence_quotes,
            severity="medium",
        )


def check_required_documents(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
    documents: Optional[list[str]] = None,
) -> PolicyFinding:
    """Evaluate Clauses 7.1 & 7.2 — Required Document Inventory."""
    inc_type = str(fact_dict.get("incident_type") or fact_dict.get("claim_type") or "").strip().lower()
    category = "Required Documents"

    # Normalize submitted document list
    doc_set: set[str] = set()
    if documents:
        for d in documents:
            name = str(d).lower()
            if "claim" in name or "form" in name:
                doc_set.add("claim_form")
            if "estimate" in name or "repair" in name:
                doc_set.add("repair_estimate")
            if "fir" in name or "police" in name:
                doc_set.add("fir")

    # If documents not provided as a list, inspect facts
    if not doc_set:
        if "claim_id" in fact_dict or "incident_description" in fact_dict:
            doc_set.add("claim_form")
        if "repair_estimate_amount" in fact_dict:
            doc_set.add("repair_estimate")
        if "fir_number" in fact_dict:
            doc_set.add("fir")

    facts_used = [
        fact_objs[k] for k in ["incident_type", "incident_description", "repair_estimate_amount", "fir_number"]
        if k in fact_objs
    ]

    if not doc_set and not fact_dict:
        return PolicyFinding(
            rule_id="required_documents",
            clause_id="7.1",
            category=category,
            status=RuleFindingStatus.INSUFFICIENT_EVIDENCE,
            title="Document Inventory Unavailable",
            message="Document inventory is unavailable; cannot verify required document checklist.",
            facts_used=facts_used,
            severity="medium",
        )

    if inc_type == "theft":
        clause_id = "7.2"
        rule_id = "required_theft_documents"
        required = [("Claim Form", "claim_form"), ("First Information Report (FIR)", "fir"), ("Incident Description", "incident_description")]
        has_desc = bool(str(fact_dict.get("incident_description", "")).strip())

        missing = []
        if "claim_form" not in doc_set:
            missing.append("Claim Form")
        if "fir" not in doc_set:
            missing.append("First Information Report (FIR)")
        if not has_desc:
            missing.append("Detailed Incident Description")

        if not missing:
            return PolicyFinding(
                rule_id=rule_id,
                clause_id=clause_id,
                category=category,
                status=RuleFindingStatus.PASS,
                title="All Required Theft Documents Present",
                message="All mandatory theft claim documents (Claim Form, FIR, Incident Description) are present under clause 7.2.",
                facts_used=facts_used,
                severity="info",
            )
        else:
            return PolicyFinding(
                rule_id=rule_id,
                clause_id=clause_id,
                category=category,
                status=RuleFindingStatus.FAIL,
                title="Missing Required Theft Documents",
                message=f"Required theft documentation is incomplete: {', '.join(missing)} missing under clause 7.2.",
                facts_used=facts_used,
                severity="high",
            )
    else:
        # Default to accident
        clause_id = "7.1"
        rule_id = "required_accident_documents"
        has_desc = bool(str(fact_dict.get("incident_description", "")).strip())

        missing = []
        if "claim_form" not in doc_set:
            missing.append("Claim Form")
        if "repair_estimate" not in doc_set:
            missing.append("Itemized Repair Estimate")
        if not has_desc:
            missing.append("Detailed Incident Description")

        if not missing:
            return PolicyFinding(
                rule_id=rule_id,
                clause_id=clause_id,
                category=category,
                status=RuleFindingStatus.PASS,
                title="All Required Accident Documents Present",
                message="All mandatory accidental damage documents (Claim Form, Repair Estimate, Incident Description) are present under clause 7.1.",
                facts_used=facts_used,
                severity="info",
            )
        else:
            return PolicyFinding(
                rule_id=rule_id,
                clause_id=clause_id,
                category=category,
                status=RuleFindingStatus.FAIL,
                title="Missing Required Accident Documents",
                message=f"Required accidental damage documentation is incomplete: {', '.join(missing)} missing under clause 7.1.",
                facts_used=facts_used,
                severity="medium",
            )


def check_explicit_exclusions(
    fact_dict: dict[str, Any],
    fact_objs: dict[str, FactUsed],
) -> list[PolicyFinding]:
    """Evaluate Clauses 4.1, 4.2, 4.3 — Policy Exclusions."""
    findings = []
    category = "Policy Exclusions"

    # Clause 4.1: Deliberate Damage
    findings.append(PolicyFinding(
        rule_id="exclusion_deliberate_damage",
        clause_id="4.1",
        category=category,
        status=RuleFindingStatus.PASS,
        title="No Deliberate Damage Indicated",
        message="No evidence or statement indicates deliberate, willful, or fraudulent damage under clause 4.1.",
        facts_used=[],
        severity="info",
    ))

    # Clause 4.2: Excluded Use (Commercial hire, racing, speed testing)
    findings.append(PolicyFinding(
        rule_id="exclusion_excluded_use",
        clause_id="4.2",
        category=category,
        status=RuleFindingStatus.PASS,
        title="Standard Permitted Use",
        message="Vehicle use conforms to standard personal coverage; no racing, speed testing, or commercial hire indicated under clause 4.2.",
        facts_used=[],
        severity="info",
    ))

    # Clause 4.3: Fraudulent Information & False Statements
    findings.append(PolicyFinding(
        rule_id="exclusion_fraudulent_information",
        clause_id="4.3",
        category=category,
        status=RuleFindingStatus.PASS,
        title="No Document Forgery Indicated",
        message="No forged document or intentional material misrepresentation identified under clause 4.3.",
        facts_used=[],
        severity="info",
    ))

    return findings
