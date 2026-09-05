"""ClaimLens Structured Audit Report Generator (Milestone 7).

Generates a unified, audit-ready claims evidence review report with:
- Full evidence provenance (source document, page number, verbatim quotation)
- Grounded policy clauses and deterministic rule evaluations
- Cross-document contradiction and completeness analysis
- Review status and actionable reviewer recommendations
- Strict non-adjudication disclaimers
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, Union
from pydantic import BaseModel, Field

from src.models import ExtractedFact
from src.retrieval.grounding import GroundedClause
from src.rules.policy_rules import PolicyFinding, RuleFindingStatus
from src.analysis.contradiction_detector import ContradictionFinding
from src.analysis.completeness_checker import CompletenessFinding, determine_claim_type
from src.review.recommendation_engine import (
    ReviewRecommendationEngine,
    ReviewRecommendation,
    ReviewStatus,
)

logger = logging.getLogger("claimlens.audit_report")

STANDARD_DISCLAIMER = (
    "ClaimLens provides evidence review assistance and does not make final insurance claim decisions. "
    "All findings, policy evaluations, and recommendations are structured for human claims investigator review."
)


class EvidenceReference(BaseModel):
    """An auditable piece of evidence linking a claim fact to its source quotation."""
    document_name: str = Field(..., description="Source document file name")
    page_number: int = Field(1, description="1-indexed page number in the source document")
    evidence_text: str = Field(..., description="Exact verbatim text quotation from the document")
    field_name: Optional[str] = Field(None, description="Extracted fact field or requirement name")
    value: Optional[Any] = Field(None, description="Extracted or referenced value")
    clause_id: Optional[str] = Field(None, description="Associated policy clause citation if applicable")


class ClaimSummaryDetails(BaseModel):
    """Core summary metadata for the evaluated claim."""
    claim_id: str = Field(..., description="Claim identifier (e.g. CLM-001)")
    claim_type: str = Field("ACCIDENT", description="Determined claim type (ACCIDENT, THEFT, UNKNOWN)")
    incident_date: Optional[str] = Field(None, description="Incident occurrence date")
    notification_date: Optional[str] = Field(None, description="Claim intimation date")
    vehicle_registration: Optional[str] = Field(None, description="Vehicle registration number")
    vehicle_make_model: Optional[str] = Field(None, description="Make and model of the vehicle")
    claimed_amount: Optional[float] = Field(None, description="Amount claimed by policyholder")
    repair_estimate_amount: Optional[float] = Field(None, description="Repair estimate total if applicable")
    document_count: int = Field(0, description="Total number of submitted claim documents")


class AuditReport(BaseModel):
    """Complete, structured audit report for a human insurance claims reviewer."""
    claim_id: str = Field(..., description="Claim ID")
    generated_at: str = Field(..., description="UTC ISO timestamp of report generation")
    claim_type: str = Field("ACCIDENT", description="ACCIDENT | THEFT | UNKNOWN")
    claim_summary: ClaimSummaryDetails = Field(..., description="High-level claim summary details")
    extracted_facts: list[ExtractedFact] = Field(default_factory=list, description="Extracted structured facts with evidence")
    document_inventory: list[str] = Field(default_factory=list, description="List of recognized submitted documents")
    policy_clauses: list[GroundedClause] = Field(default_factory=list, description="Grounded canonical policy clauses")
    policy_findings: list[PolicyFinding] = Field(default_factory=list, description="Deterministic policy rule evaluations")
    contradictions: list[ContradictionFinding] = Field(default_factory=list, description="Factual cross-document contradictions")
    completeness_findings: list[CompletenessFinding] = Field(default_factory=list, description="Document completeness evaluations")
    recommendation: ReviewRecommendation = Field(..., description="Review recommendation and action")
    evidence_references: list[EvidenceReference] = Field(default_factory=list, description="Consolidated auditable evidence citations")
    disclaimer: str = Field(STANDARD_DISCLAIMER, description="Non-adjudication disclaimer")

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)


class AuditReportGenerator:
    """Orchestrates all review components to compile a comprehensive AuditReport."""

    def __init__(self, recommendation_engine: Optional[ReviewRecommendationEngine] = None):
        self.recommendation_engine = recommendation_engine or ReviewRecommendationEngine()

    def generate_report(
        self,
        claim_id: str,
        facts: Optional[Union[list[Any], dict[str, Any]]] = None,
        documents: Optional[list[Any]] = None,
        retrieved_clauses: Optional[list[Union[GroundedClause, dict[str, Any]]]] = None,
        policy_findings: Optional[list[Union[PolicyFinding, dict[str, Any]]]] = None,
        contradictions: Optional[list[Union[ContradictionFinding, dict[str, Any]]]] = None,
        completeness_findings: Optional[list[Union[CompletenessFinding, dict[str, Any]]]] = None,
        recommendation: Optional[Union[ReviewRecommendation, dict[str, Any]]] = None,
    ) -> AuditReport:
        """Compile a fully structured audit report."""
        norm_facts = self._normalize_facts(facts or [])
        doc_names = self._normalize_document_names(documents or [], facts)
        norm_clauses = self._normalize_clauses(retrieved_clauses or [])
        norm_p_findings = self._normalize_policy_findings(policy_findings or [])
        norm_contradictions = self._normalize_contradictions(contradictions or [])
        norm_completeness = self._normalize_completeness(completeness_findings or [])

        # Determine claim type
        claim_type = determine_claim_type(facts=norm_facts, documents=doc_names)

        # Recommendation
        if recommendation is None:
            rec = self.recommendation_engine.evaluate(
                policy_findings=norm_p_findings,
                contradictions=norm_contradictions,
                completeness_findings=norm_completeness,
            )
        elif isinstance(recommendation, ReviewRecommendation):
            rec = recommendation
        elif isinstance(recommendation, dict):
            rec = ReviewRecommendation(**recommendation)
        else:
            rec = self.recommendation_engine.evaluate(
                policy_findings=norm_p_findings,
                contradictions=norm_contradictions,
                completeness_findings=norm_completeness,
            )

        # Build claim summary
        summary = self._build_claim_summary(claim_id, claim_type, norm_facts, doc_names)

        # Build evidence references provenance
        ev_refs = self._build_evidence_references(
            norm_facts, norm_contradictions, norm_completeness, doc_names
        )

        report = AuditReport(
            claim_id=claim_id or "CLM-UNKNOWN",
            generated_at=datetime.now(timezone.utc).isoformat(),
            claim_type=claim_type,
            claim_summary=summary,
            extracted_facts=norm_facts,
            document_inventory=doc_names,
            policy_clauses=norm_clauses,
            policy_findings=norm_p_findings,
            contradictions=norm_contradictions,
            completeness_findings=norm_completeness,
            recommendation=rec,
            evidence_references=ev_refs,
            disclaimer=STANDARD_DISCLAIMER,
        )
        return report

    # ── Normalizers & Builders ────────────────────────────────────────────

    def _normalize_facts(self, raw_facts: Union[list[Any], dict[str, Any]]) -> list[ExtractedFact]:
        facts_list: list[ExtractedFact] = []
        if isinstance(raw_facts, list):
            for item in raw_facts:
                if isinstance(item, ExtractedFact):
                    facts_list.append(item)
                elif isinstance(item, dict):
                    if "field_name" in item:
                        try:
                            facts_list.append(ExtractedFact(**item))
                        except Exception:
                            pass
                    elif "facts" in item and isinstance(item["facts"], list):
                        # DocumentFactBundle
                        doc_name = item.get("document_name", "document.pdf")
                        for f in item["facts"]:
                            if isinstance(f, ExtractedFact):
                                facts_list.append(f)
                            elif isinstance(f, dict):
                                try:
                                    f_copy = dict(f)
                                    facts_list.append(ExtractedFact(**f_copy))
                                except Exception:
                                    pass
        elif isinstance(raw_facts, dict):
            for k, v in raw_facts.items():
                facts_list.append(
                    ExtractedFact(
                        field_name=k,
                        value=v,
                        raw_value=str(v) if v is not None else None,
                        evidence_text=f"{k}: {v}",
                        page_number=1,
                    )
                )
        return facts_list

    def _normalize_document_names(
        self, docs: list[Any], facts: Optional[list[ExtractedFact]] = None
    ) -> list[str]:
        names: list[str] = []
        for d in docs:
            if isinstance(d, str):
                names.append(d)
            elif isinstance(d, dict):
                names.append(d.get("filename") or d.get("document_name") or d.get("name") or "document.pdf")
            elif hasattr(d, "filename"):
                names.append(d.filename)
            elif hasattr(d, "document_name"):
                names.append(d.document_name)
        if not names and isinstance(facts, list):
            for f in facts:
                if isinstance(f, dict) and "document_name" in f:
                    names.append(f["document_name"])
        return sorted(list(set(names))) if names else ["claim_form.pdf"]

    def _normalize_clauses(
        self, clauses: list[Union[GroundedClause, dict[str, Any]]]
    ) -> list[GroundedClause]:
        norm = []
        for c in clauses:
            if isinstance(c, GroundedClause):
                norm.append(c)
            elif isinstance(c, dict):
                try:
                    norm.append(GroundedClause(**c))
                except Exception:
                    pass
        return norm

    def _normalize_policy_findings(
        self, findings: list[Union[PolicyFinding, dict[str, Any]]]
    ) -> list[PolicyFinding]:
        norm = []
        for f in findings:
            if isinstance(f, PolicyFinding):
                norm.append(f)
            elif isinstance(f, dict):
                try:
                    norm.append(PolicyFinding(**f))
                except Exception:
                    pass
        return norm

    def _normalize_contradictions(
        self, contradictions: list[Union[ContradictionFinding, dict[str, Any]]]
    ) -> list[ContradictionFinding]:
        norm = []
        for c in contradictions:
            if isinstance(c, ContradictionFinding):
                norm.append(c)
            elif isinstance(c, dict):
                try:
                    norm.append(ContradictionFinding(**c))
                except Exception:
                    pass
        return norm

    def _normalize_completeness(
        self, completeness: list[Union[CompletenessFinding, dict[str, Any]]]
    ) -> list[CompletenessFinding]:
        norm = []
        for cf in completeness:
            if isinstance(cf, CompletenessFinding):
                norm.append(cf)
            elif isinstance(cf, dict):
                try:
                    norm.append(CompletenessFinding(**cf))
                except Exception:
                    pass
        return norm

    def _build_claim_summary(
        self,
        claim_id: str,
        claim_type: str,
        facts: list[ExtractedFact],
        doc_names: list[str],
    ) -> ClaimSummaryDetails:
        f_map = {f.field_name: f.value for f in facts}
        make = f_map.get("vehicle_make")
        model = f_map.get("vehicle_model")
        make_model = None
        if make and model:
            make_model = f"{make} {model}"
        elif make or model:
            make_model = str(make or model)

        claimed = f_map.get("claimed_amount")
        try:
            claimed_val = float(claimed) if claimed is not None else None
        except (ValueError, TypeError):
            claimed_val = None

        repair_est = f_map.get("repair_estimate_amount")
        try:
            repair_val = float(repair_est) if repair_est is not None else None
        except (ValueError, TypeError):
            repair_val = None

        return ClaimSummaryDetails(
            claim_id=claim_id or "CLM-UNKNOWN",
            claim_type=claim_type,
            incident_date=str(f_map.get("incident_date")) if f_map.get("incident_date") else None,
            notification_date=str(f_map.get("notification_date")) if f_map.get("notification_date") else None,
            vehicle_registration=str(f_map.get("vehicle_registration")) if f_map.get("vehicle_registration") else None,
            vehicle_make_model=make_model,
            claimed_amount=claimed_val,
            repair_estimate_amount=repair_val,
            document_count=len(doc_names),
        )

    def _build_evidence_references(
        self,
        facts: list[ExtractedFact],
        contradictions: list[ContradictionFinding],
        completeness: list[CompletenessFinding],
        doc_names: list[str],
    ) -> list[EvidenceReference]:
        refs: list[EvidenceReference] = []
        seen = set()

        # From extracted facts
        primary_doc = doc_names[0] if doc_names else "claim_form.pdf"
        for f in facts:
            if f.evidence_text and f.evidence_text.strip():
                key = (f.evidence_text, f.page_number, f.field_name)
                if key not in seen:
                    seen.add(key)
                    refs.append(
                        EvidenceReference(
                            document_name=primary_doc,
                            page_number=f.page_number or 1,
                            evidence_text=f.evidence_text,
                            field_name=f.field_name,
                            value=f.value,
                        )
                    )

        # From contradictions
        for c in contradictions:
            if c.evidence_a and (c.evidence_a, c.page_a, c.field_name) not in seen:
                seen.add((c.evidence_a, c.page_a, c.field_name))
                refs.append(
                    EvidenceReference(
                        document_name=c.document_a,
                        page_number=c.page_a or 1,
                        evidence_text=c.evidence_a,
                        field_name=c.field_name,
                        value=c.value_a,
                    )
                )
            if c.evidence_b and (c.evidence_b, c.page_b, c.field_name) not in seen:
                seen.add((c.evidence_b, c.page_b, c.field_name))
                refs.append(
                    EvidenceReference(
                        document_name=c.document_b,
                        page_number=c.page_b or 1,
                        evidence_text=c.evidence_b,
                        field_name=c.field_name,
                        value=c.value_b,
                    )
                )

        return refs
