"""Unit and integration tests for Milestone 5 Deterministic Policy Rules."""

import pytest
from fastapi.testclient import TestClient

from app import app
from src.models import ExtractedFact, ClaimFacts
from src.rules.policy_rules import (
    PolicyFinding,
    RuleFindingStatus,
    extract_fact_dict,
    check_coverage_period,
    check_covered_vehicle,
    check_accident_coverage,
    check_repair_settlement,
    check_theft_coverage,
    check_fir_requirement,
    check_idv_valuation,
    check_notification_window,
    check_required_documents,
    check_explicit_exclusions,
)
from src.rules.rule_engine import PolicyRuleEngine, PolicyEvaluationResult
from src.rules.coverage import evaluate_coverage
from src.rules.documents import check_document_completeness

client = TestClient(app)


# ── 1. Coverage Period Tests (Clause 1.1) ────────────────────────────────

def test_coverage_period_within_range():
    """Incident date within policy period passes."""
    facts = {"incident_date": "2026-08-20"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_coverage_period(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "1.1"
    assert "within" in finding.message.lower()


def test_coverage_period_before_start():
    """Incident date before policy start date fails."""
    facts = {"incident_date": "2025-12-15"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_coverage_period(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.FAIL
    assert finding.clause_id == "1.1"
    assert "outside" in finding.message.lower()


def test_coverage_period_after_end():
    """Incident date after policy expiry fails."""
    facts = {"incident_date": "2027-01-10"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_coverage_period(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.FAIL
    assert finding.clause_id == "1.1"


def test_coverage_period_missing_date():
    """Missing incident date returns INSUFFICIENT_EVIDENCE."""
    facts = {}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_coverage_period(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.INSUFFICIENT_EVIDENCE
    assert finding.clause_id == "1.1"


# ── 2. Covered Vehicle Tests (Clause 1.2) ────────────────────────────────

def test_covered_vehicle_present():
    """Valid vehicle registration passes."""
    facts = {
        "vehicle_registration": "TN01AB1234",
        "vehicle_make": "Hyundai",
        "vehicle_model": "i20",
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_covered_vehicle(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "1.2"
    assert "TN01AB1234" in finding.message


def test_covered_vehicle_missing_registration():
    """Missing registration returns INSUFFICIENT_EVIDENCE."""
    facts = {"vehicle_make": "Hyundai"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_covered_vehicle(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.INSUFFICIENT_EVIDENCE
    assert finding.clause_id == "1.2"


# ── 3. Accidental Damage Coverage Tests (Clause 2.1) ──────────────────────

def test_accident_coverage_accident_claim():
    """Accident claim passes accidental damage coverage rule."""
    facts = {"incident_type": "accident"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_accident_coverage(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "2.1"


def test_accident_coverage_theft_claim():
    """Theft claim returns NOT_APPLICABLE for accidental damage."""
    facts = {"incident_type": "theft"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_accident_coverage(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.NOT_APPLICABLE
    assert finding.clause_id == "2.1"


def test_accident_coverage_unknown_type():
    """Missing incident type returns INSUFFICIENT_EVIDENCE."""
    facts = {}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_accident_coverage(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.INSUFFICIENT_EVIDENCE


# ── 4. Repair Settlement Assessment Tests (Clause 2.2) ───────────────────

def test_repair_settlement_with_amount():
    """Repair estimate amount provided passes."""
    facts = {"incident_type": "accident", "repair_estimate_amount": 78000}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_repair_settlement(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "2.2"
    assert "78,000" in finding.message


def test_repair_settlement_with_document():
    """Repair estimate document provided passes."""
    facts = {"incident_type": "accident"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_repair_settlement(fact_dict, fact_objs, documents=["repair_estimate.pdf"])

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "2.2"


def test_repair_settlement_missing_for_accident():
    """Missing repair estimate for accident claim fails."""
    facts = {"incident_type": "accident"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_repair_settlement(fact_dict, fact_objs, documents=["claim_form.pdf"])

    assert finding.status == RuleFindingStatus.FAIL
    assert finding.clause_id == "2.2"


def test_repair_settlement_theft_not_applicable():
    """Theft claim returns NOT_APPLICABLE for repair settlement."""
    facts = {"incident_type": "theft"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_repair_settlement(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.NOT_APPLICABLE


# ── 5. Theft Coverage Tests (Clause 3.1) ─────────────────────────────────

def test_theft_coverage_theft_claim():
    """Theft claim passes theft coverage rule."""
    facts = {"incident_type": "theft"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_theft_coverage(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "3.1"


def test_theft_coverage_accident_claim():
    """Accident claim returns NOT_APPLICABLE for theft coverage."""
    facts = {"incident_type": "accident"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_theft_coverage(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.NOT_APPLICABLE


# ── 6. FIR Requirement Tests (Clause 3.2) ────────────────────────────────

def test_fir_requirement_theft_with_fir_doc():
    """Theft claim with FIR document passes."""
    facts = {"incident_type": "theft"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_fir_requirement(fact_dict, fact_objs, documents=["claim_form.pdf", "fir.pdf"])

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "3.2"


def test_fir_requirement_theft_with_missing_fir():
    """Theft claim without FIR document fails under clause 3.2."""
    facts = {"incident_type": "theft"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_fir_requirement(fact_dict, fact_objs, documents=["claim_form.pdf"])

    assert finding.status == RuleFindingStatus.FAIL
    assert finding.clause_id == "3.2"
    assert "required for theft" in finding.message.lower()


def test_fir_requirement_accident_claim_not_applicable():
    """Accident claim returns NOT_APPLICABLE for theft FIR requirement."""
    facts = {"incident_type": "accident"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_fir_requirement(fact_dict, fact_objs, documents=["claim_form.pdf"])

    assert finding.status == RuleFindingStatus.NOT_APPLICABLE


# ── 7. IDV & Valuation Tests (Clauses 5.1 & 5.2) ─────────────────────────

def test_idv_valuation_within_limit():
    """Claimed amount within IDV passes."""
    facts = {"claimed_amount": 78000, "idv": 100000}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_idv_valuation(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert "within" in finding.message.lower()


def test_idv_valuation_exceeds_limit():
    """Claimed amount exceeding IDV produces WARNING (not auto-reject)."""
    facts = {"claimed_amount": 120000, "idv": 100000}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_idv_valuation(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.WARNING
    assert "exceeds" in finding.message.lower()


def test_idv_valuation_missing_amount():
    """Missing claimed amount returns INSUFFICIENT_EVIDENCE."""
    facts = {}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_idv_valuation(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.INSUFFICIENT_EVIDENCE


# ── 8. Notification Window Tests (Clauses 6.1 & 6.2) ─────────────────────

def test_notification_window_within_7_days():
    """Notification within 7 days passes."""
    facts = {
        "incident_date": "2026-08-20",
        "notification_date": "2026-08-22",  # 2 days
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_notification_window(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "6.1"
    assert "within" in finding.message.lower()


def test_notification_window_late_notification_produces_warning():
    """Notification after 7 days produces WARNING under clause 6.2 (never FAIL)."""
    facts = {
        "incident_date": "2026-08-01",
        "notification_date": "2026-08-15",  # 14 days
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_notification_window(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.WARNING
    assert finding.clause_id == "6.2"
    assert "investigator review" in finding.message.lower()
    # Must NOT be FAIL
    assert finding.status != RuleFindingStatus.FAIL


def test_notification_window_missing_date():
    """Missing notification date returns INSUFFICIENT_EVIDENCE."""
    facts = {"incident_date": "2026-08-20"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_notification_window(fact_dict, fact_objs)

    assert finding.status == RuleFindingStatus.INSUFFICIENT_EVIDENCE


# ── 9. Required Documents Tests (Clauses 7.1 & 7.2) ──────────────────────

def test_required_accident_documents_complete():
    """Accident claim with all required documents passes clause 7.1."""
    facts = {
        "incident_type": "accident",
        "incident_description": "Collision with guardrail",
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_required_documents(
        fact_dict, fact_objs, documents=["claim_form.pdf", "repair_estimate.pdf"]
    )

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "7.1"


def test_required_accident_documents_missing_estimate():
    """Accident claim missing repair estimate fails clause 7.1."""
    facts = {
        "incident_type": "accident",
        "incident_description": "Collision with guardrail",
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_required_documents(
        fact_dict, fact_objs, documents=["claim_form.pdf"]
    )

    assert finding.status == RuleFindingStatus.FAIL
    assert finding.clause_id == "7.1"
    assert "Repair Estimate" in finding.message


def test_required_theft_documents_complete():
    """Theft claim with all required documents passes clause 7.2."""
    facts = {
        "incident_type": "theft",
        "incident_description": "Vehicle stolen from parking",
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_required_documents(
        fact_dict, fact_objs, documents=["claim_form.pdf", "fir.pdf"]
    )

    assert finding.status == RuleFindingStatus.PASS
    assert finding.clause_id == "7.2"


def test_required_theft_documents_missing_fir():
    """Theft claim missing FIR fails clause 7.2."""
    facts = {
        "incident_type": "theft",
        "incident_description": "Vehicle stolen from parking",
    }
    fact_dict, fact_objs = extract_fact_dict(facts)
    finding = check_required_documents(
        fact_dict, fact_objs, documents=["claim_form.pdf"]
    )

    assert finding.status == RuleFindingStatus.FAIL
    assert finding.clause_id == "7.2"
    assert "FIR" in finding.message or "First Information Report" in finding.message


# ── 10. Exclusions Tests (Clauses 4.1, 4.2, 4.3) ─────────────────────────

def test_explicit_exclusions_pass_by_default():
    """Explicit exclusions evaluate cleanly for standard claims."""
    facts = {"incident_type": "accident"}
    fact_dict, fact_objs = extract_fact_dict(facts)
    findings = check_explicit_exclusions(fact_dict, fact_objs)

    assert len(findings) == 3
    assert all(f.status == RuleFindingStatus.PASS for f in findings)
    clause_ids = [f.clause_id for f in findings]
    assert "4.1" in clause_ids
    assert "4.2" in clause_ids
    assert "4.3" in clause_ids


# ── 11. PolicyRuleEngine Orchestrator Tests ──────────────────────────────

def test_rule_engine_clean_accident_clm_001():
    """CLM-001 (Clean accident) satisfies all applicable policy conditions."""
    engine = PolicyRuleEngine()
    facts = [
        ExtractedFact(field_name="incident_type", value="accident", raw_value="accident", page_number=1),
        ExtractedFact(field_name="vehicle_registration", value="TN01AB1234", raw_value="TN01AB1234", page_number=1),
        ExtractedFact(field_name="vehicle_make", value="Hyundai", raw_value="Hyundai", page_number=1),
        ExtractedFact(field_name="vehicle_model", value="i20", raw_value="i20", page_number=1),
        ExtractedFact(field_name="incident_date", value="2026-08-20", raw_value="20 Aug 2026", page_number=1),
        ExtractedFact(field_name="notification_date", value="2026-08-22", raw_value="22 Aug 2026", page_number=1),
        ExtractedFact(field_name="claimed_amount", value=78000, raw_value="₹78,000", page_number=1),
        ExtractedFact(field_name="repair_estimate_amount", value=78000, raw_value="₹78,000", page_number=1),
        ExtractedFact(field_name="incident_description", value="Front collision with tree", raw_value="...", page_number=1),
    ]
    docs = ["claim_form.pdf", "repair_estimate.pdf"]

    result = engine.evaluate(facts, documents=docs, claim_id="CLM-001")

    assert result.claim_id == "CLM-001"
    assert result.summary.total_rules_checked >= 10
    assert result.summary.fail_count == 0
    assert result.summary.warning_count == 0
    assert result.summary.pass_count >= 8

    # Ensure no adjudication decisions in any finding text
    for f in result.findings:
        assert "APPROVE" not in f.message
        assert "REJECT" not in f.message
        assert "DENY" not in f.message
        assert "FRAUD" not in f.message


def test_rule_engine_theft_missing_fir_clm_003():
    """CLM-003 (Theft with missing FIR) fails FIR & doc rules, passes theft rules."""
    engine = PolicyRuleEngine()
    facts = [
        ExtractedFact(field_name="incident_type", value="theft", raw_value="theft", page_number=1),
        ExtractedFact(field_name="vehicle_registration", value="TN03EF9012", raw_value="TN03EF9012", page_number=1),
        ExtractedFact(field_name="incident_date", value="2026-08-25", raw_value="25 Aug 2026", page_number=1),
        ExtractedFact(field_name="notification_date", value="2026-08-26", raw_value="26 Aug 2026", page_number=1),
        ExtractedFact(field_name="claimed_amount", value=72000, raw_value="₹72,000", page_number=1),
        ExtractedFact(field_name="incident_description", value="Vehicle stolen from parking", raw_value="...", page_number=1),
    ]
    docs = ["claim_form.pdf"]  # FIR missing

    result = engine.evaluate(facts, documents=docs, claim_id="CLM-003")

    assert result.claim_id == "CLM-003"
    assert result.summary.fail_count >= 2  # Clause 3.2 and Clause 7.2

    # Verify Clause 3.2 and 7.2 specifically failed
    finding_map = {f.clause_id: f for f in result.findings}
    assert finding_map["3.2"].status == RuleFindingStatus.FAIL
    assert finding_map["7.2"].status == RuleFindingStatus.FAIL

    # Theft coverage clause 3.1 should pass
    assert finding_map["3.1"].status == RuleFindingStatus.PASS
    # Accidental damage clause 2.1 should be NOT_APPLICABLE
    assert finding_map["2.1"].status == RuleFindingStatus.NOT_APPLICABLE


# ── 12. API Endpoint Tests (/api/evaluate-policy) ────────────────────────

def test_evaluate_policy_endpoint_with_facts_list():
    """POST /api/evaluate-policy succeeds with ExtractedFact list."""
    payload = {
        "claim_id": "CLM-TEST-01",
        "facts": [
            {"field_name": "incident_type", "value": "accident", "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "vehicle_registration", "value": "KA01MN1234", "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "incident_date", "value": "2026-07-10", "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "notification_date", "value": "2026-07-12", "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "claimed_amount", "value": 45000, "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "repair_estimate_amount", "value": 45000, "page_number": 1, "confidence": 1.0, "evidence_valid": True},
            {"field_name": "incident_description", "value": "Side collision", "page_number": 1, "confidence": 1.0, "evidence_valid": True},
        ],
        "documents": ["claim_form.pdf", "repair_estimate.pdf"],
    }

    response = client.post("/api/evaluate-policy", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["claim_id"] == "CLM-TEST-01"
    assert len(data["findings"]) >= 10
    assert data["summary"]["pass_count"] >= 8


def test_evaluate_policy_endpoint_with_dict_facts():
    """POST /api/evaluate-policy succeeds with claim_facts dictionary."""
    payload = {
        "claim_id": "CLM-TEST-02",
        "claim_facts": {
            "incident_type": "accident",
            "vehicle_registration": "MH02CD3456",
            "incident_date": "2026-05-10",
            "notification_date": "2026-05-11",
            "claimed_amount": 50000,
            "repair_estimate_amount": 50000,
            "incident_description": "Rear bumper hit",
        },
        "documents": ["claim_form.pdf", "repair_estimate.pdf"],
    }

    response = client.post("/api/evaluate-policy", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["claim_id"] == "CLM-TEST-02"
    assert data["summary"]["fail_count"] == 0


def test_evaluate_coverage_module_function():
    """evaluate_coverage helper in src.rules.coverage executes cleanly."""
    facts = {
        "incident_type": "accident",
        "vehicle_registration": "DL01XY9999",
        "incident_date": "2026-04-15",
        "claimed_amount": 30000,
    }
    findings = evaluate_coverage(facts)
    assert len(findings) == 5
    assert all(isinstance(f, PolicyFinding) for f in findings)


def test_check_document_completeness_module_function():
    """check_document_completeness in src.rules.documents executes cleanly."""
    findings = check_document_completeness(
        documents=["claim_form.pdf", "repair_estimate.pdf"],
        facts={"incident_type": "accident", "incident_description": "Scratches on door", "repair_estimate_amount": 12000},
    )
    assert len(findings) == 3
    assert all(isinstance(f, PolicyFinding) for f in findings)
