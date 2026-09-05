"""Verification and demonstration script for Milestone 5 Deterministic Policy Rules.

Evaluates synthetic demo claims (CLM-001, CLM-002, CLM-003) against the 16-clause
canonical motor policy.

Strict Decision Boundary:
- Strictly does NOT print APPROVE, REJECT, DENY, FRAUD, or final claim adjudication.
- Prints auditable rule finding statuses: PASS, FAIL, WARNING, INSUFFICIENT_EVIDENCE, NOT_APPLICABLE.

Usage:
    python scripts/test_policy_rules.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.rules.rule_engine import PolicyRuleEngine, RuleFindingStatus

DEMO_DIR = BASE_DIR / "data" / "demo_claims"


def run_policy_rules_verification() -> int:
    print("=" * 68)
    print("ClaimLens — Deterministic Policy Rule Engine Verification (Milestone 5)")
    print("=" * 68)
    print("Decision Boundary: Evidence First. Decisions Second.")
    print("Rule evaluation identifies policy conditions and evidence gaps without")
    print("making final claim approval, rejection, or fraud determinations.")
    print("-" * 68)

    engine = PolicyRuleEngine()

    cases = [
        ("CLM-001", "Clean Accident (Supported)", DEMO_DIR / "claim_001_clean_accident"),
        ("CLM-002", "Contradictory Accident (Discrepancies in facts)", DEMO_DIR / "claim_002_contradiction"),
        ("CLM-003", "Theft Claim (Missing Mandatory FIR)", DEMO_DIR / "claim_003_missing_fir"),
    ]

    all_passed = True

    for claim_id, description, claim_path in cases:
        print("\n" + "=" * 68)
        print(f"EVALUATING CLAIM: {claim_id} — {description}")
        print("=" * 68)

        meta_file = claim_path / "metadata.json"
        if not meta_file.exists():
            print(f"[ERROR] Missing metadata file: {meta_file}")
            all_passed = False
            continue

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Build claim facts dictionary
        facts = {
            "claim_id": metadata.get("claim_id", claim_id),
            "incident_type": metadata.get("claim_type"),
            "vehicle_registration": metadata.get("vehicle_registration"),
            "vehicle_make": metadata.get("vehicle_make"),
            "vehicle_model": metadata.get("vehicle_model"),
            "incident_date": metadata.get("incident_date"),
            "notification_date": metadata.get("notification_date"),
            "claimed_amount": metadata.get("claimed_amount"),
            "repair_estimate_amount": metadata.get("repair_estimate_amount"),
            "incident_description": metadata.get("incident_description"),
        }

        # For CLM-002 nested claim form values if present
        if "claim_form" in metadata:
            cf = metadata["claim_form"]
            for k, v in cf.items():
                if k not in facts or facts[k] is None:
                    facts[k] = v

        # Determine document inventory from directory files
        pdf_docs = [p.name for p in claim_path.glob("*.pdf")]

        result = engine.evaluate(
            facts=facts,
            documents=pdf_docs,
            claim_id=claim_id,
        )

        print(f"Documents Ingested: {', '.join(pdf_docs) if pdf_docs else 'None'}")
        print(f"Total Rules Evaluated: {result.summary.total_rules_checked}")
        print(
            f"Summary: {result.summary.pass_count} PASS | {result.summary.fail_count} FAIL | "
            f"{result.summary.warning_count} WARNING | {result.summary.insufficient_evidence_count} INSUFFICIENT | "
            f"{result.summary.not_applicable_count} N/A"
        )
        print("-" * 68)

        # Status symbol helper
        symbols = {
            RuleFindingStatus.PASS: "[✓ PASS]",
            RuleFindingStatus.FAIL: "[✗ FAIL]",
            RuleFindingStatus.WARNING: "[⚠ WARN]",
            RuleFindingStatus.INSUFFICIENT_EVIDENCE: "[? INSUF]",
            RuleFindingStatus.NOT_APPLICABLE: "[— N/A ]",
        }

        for idx, finding in enumerate(result.findings, 1):
            sym = symbols.get(finding.status, "[?]")
            print(f"{idx:2d}. {sym} Clause {finding.clause_id:4s} | {finding.title} ({finding.category})")
            print(f"    Message: {finding.message}")

        # Verification asserts for each case
        if claim_id == "CLM-001":
            if result.summary.fail_count != 0 or result.summary.warning_count != 0:
                print(f"[FAIL] Expected 0 FAIL and 0 WARNING for CLM-001, got {result.summary.fail_count} FAIL, {result.summary.warning_count} WARN")
                all_passed = False
            else:
                print(f"[OK] {claim_id} evaluated with 0 policy rule failures.")

        elif claim_id == "CLM-003":
            finding_map = {f.clause_id: f for f in result.findings}
            if finding_map.get("3.2", None) is None or finding_map["3.2"].status != RuleFindingStatus.FAIL:
                print("[FAIL] Expected Clause 3.2 (Mandatory FIR) to FAIL for CLM-003")
                all_passed = False
            elif finding_map.get("7.2", None) is None or finding_map["7.2"].status != RuleFindingStatus.FAIL:
                print("[FAIL] Expected Clause 7.2 (Required Theft Docs) to FAIL for CLM-003")
                all_passed = False
            else:
                print(f"[OK] {claim_id} correctly triggered mandatory FIR failure under Clause 3.2 and 7.2.")

    print("\n" + "=" * 68)
    if all_passed:
        print("ALL DEMO CLAIMS EVALUATED SUCCESSFULLY")
        print("Milestone 5 rule evaluation completed.")
        return 0
    else:
        print("SOME RULE EVALUATION CHECKS FAILED")
        return 1


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run_policy_rules_verification())
