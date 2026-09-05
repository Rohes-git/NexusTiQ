"""End-to-End Review Pipeline Verification Script (Milestone 7).

Executes the complete Claims Evidence Review workflow across all 3 demo claims:
1. Fact & Document Ingestion
2. Policy Clause Grounding
3. Deterministic Policy Rule Evaluation
4. Cross-Document Contradiction & Completeness Analysis
5. Review Recommendation Engine (Strict Non-Adjudication)
6. Final Audit Report Generation

Usage:
    python scripts/test_end_to_end.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
except ImportError:
    pass

from src.config import settings
from src.retrieval.policy_retriever import PolicyRetriever
from src.rules.rule_engine import PolicyRuleEngine
from src.analysis.evidence_review import EvidenceReviewEngine
from src.review.recommendation_engine import (
    ReviewRecommendationEngine,
    ReviewStatus,
    PROHIBITED_DECISION_TERMS,
)
from src.report.audit_report import AuditReportGenerator, STANDARD_DISCLAIMER

DEMO_DIR = BASE_DIR / "data" / "demo_claims"


def run_end_to_end_verification() -> int:
    print("=" * 70)
    print("ClaimLens — End-to-End Claims Evidence Review Pipeline Verification")
    print("=" * 70)

    # Initialize engines
    rule_engine = PolicyRuleEngine()
    evidence_engine = EvidenceReviewEngine()
    rec_engine = ReviewRecommendationEngine()
    report_gen = AuditReportGenerator()

    # Optional live retriever
    retriever = None
    if settings.gemini_configured:
        try:
            retriever = PolicyRetriever()
            retriever.ensure_index()
            print("[OK] Policy vector index loaded for semantic clause grounding.")
        except Exception as e:
            print(f"[WARN] Policy vector index could not be initialized: {e}")
    else:
        print("[INFO] GEMINI_API_KEY not configured. Running deterministic pipeline verification.")

    test_cases = [
        {
            "claim_id": "CLM-001",
            "name": "Clean Accident Claim",
            "meta_path": DEMO_DIR / "claim_001_clean_accident" / "metadata.json",
            "docs": ["claim_form.pdf", "repair_estimate.pdf"],
            "expected_status": ReviewStatus.READY_FOR_REVIEW,
            "expected_contradictions_count": 0,
            "expected_missing_docs_count": 0,
        },
        {
            "claim_id": "CLM-002",
            "name": "Contradictory Claim (Date & Amount Mismatch)",
            "meta_path": DEMO_DIR / "claim_002_contradiction" / "metadata.json",
            "docs": ["claim_form.pdf", "repair_estimate.pdf"],
            "expected_status": ReviewStatus.REQUEST_INFORMATION,
            "expected_contradictions_count": 2,
            "expected_missing_docs_count": 0,
        },
        {
            "claim_id": "CLM-003",
            "name": "Theft Claim (Missing Mandatory FIR)",
            "meta_path": DEMO_DIR / "claim_003_missing_fir" / "metadata.json",
            "docs": ["claim_form.pdf"],
            "expected_status": ReviewStatus.REQUEST_INFORMATION,
            "expected_contradictions_count": 0,
            "expected_missing_docs_count": 1,
        },
    ]

    all_passed = True

    for case in test_cases:
        claim_id = case["claim_id"]
        meta_path = case["meta_path"]
        docs = case["docs"]
        print(f"\n[{claim_id}] Running Pipeline for: {case['name']}")
        print("-" * 70)

        if not meta_path.exists():
            print(f"[FAIL] Missing metadata file at: {meta_path}")
            all_passed = False
            continue

        with open(meta_path, "r", encoding="utf-8") as f:
            facts = json.load(f)

        # 2. Step 3: Policy Grounding
        retrieved_clauses = []
        if retriever:
            try:
                _, retrieved_clauses = retriever.retrieve_relevant_clauses(facts, top_k=5)
                print(f"  Step 3: Grounded {len(retrieved_clauses)} relevant policy clauses.")
            except Exception as e:
                print(f"  Step 3: Retrieval skipped ({e})")
        else:
            print("  Step 3: Policy grounding simulated.")

        # 3. Step 4: Policy Rule Evaluation
        eval_result = rule_engine.evaluate(
            facts=facts,
            documents=docs,
            claim_id=claim_id,
            retrieved_clauses=retrieved_clauses,
        )
        print(f"  Step 4: Evaluated {eval_result.summary.total_rules_checked} rules "
              f"({eval_result.summary.pass_count} PASS, {eval_result.summary.fail_count} FAIL, {eval_result.summary.warning_count} WARNING).")

        # 4. Step 5: Evidence Contradiction & Completeness
        evidence_result = evidence_engine.analyze(
            claim_id=claim_id,
            facts=facts,
            documents=docs,
        )
        print(f"  Step 5: Analyzed evidence -> {len(evidence_result.contradictions)} contradictions, "
              f"{evidence_result.summary.missing_evidence_count} missing required docs.")

        # 5. Step 6: Review Recommendation
        recommendation = rec_engine.evaluate(
            policy_findings=eval_result.findings,
            contradictions=evidence_result.contradictions,
            completeness_findings=evidence_result.completeness,
        )
        print(f"  Step 6: Generated Review Recommendation -> {recommendation.status.value}")
        print(f"          Reason: {recommendation.reason}")

        # 6. Audit Report Generation
        report = report_gen.generate_report(
            claim_id=claim_id,
            facts=facts,
            documents=docs,
            retrieved_clauses=retrieved_clauses,
            policy_findings=eval_result.findings,
            contradictions=evidence_result.contradictions,
            completeness_findings=evidence_result.completeness,
        )

        # ── Validations ───────────────────────────────────────────────────
        # Validate status matches expected
        if recommendation.status != case["expected_status"]:
            print(f"[FAIL] Expected status {case['expected_status'].value}, got {recommendation.status.value}")
            all_passed = False
        else:
            print(f"[PASS] Status matches expected: {recommendation.status.value}")

        # Validate non-adjudication terms are never returned
        assert recommendation.status.value not in PROHIBITED_DECISION_TERMS, "Prohibited status term detected!"
        assert report.disclaimer == STANDARD_DISCLAIMER, "Standard disclaimer missing from audit report!"

        # Validate contradiction count
        if len(evidence_result.contradictions) != case["expected_contradictions_count"]:
            print(f"[FAIL] Expected {case['expected_contradictions_count']} contradictions, got {len(evidence_result.contradictions)}")
            all_passed = False
        else:
            print(f"[PASS] Contradictions count matches expected ({len(evidence_result.contradictions)})")

        # Validate missing doc count
        if evidence_result.summary.missing_evidence_count != case["expected_missing_docs_count"]:
            print(f"[FAIL] Expected {case['expected_missing_docs_count']} missing docs, got {evidence_result.summary.missing_evidence_count}")
            all_passed = False
        else:
            print(f"[PASS] Missing documents count matches expected ({evidence_result.summary.missing_evidence_count})")

        print(f"[OK] {claim_id} Full Pipeline Execution Verified.")

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL END-TO-END WORKFLOW TESTS PASSED SUCCESSFULLY (3/3)")
        return 0
    else:
        print("SOME END-TO-END WORKFLOW TESTS FAILED")
        return 1


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run_end_to_end_verification())
