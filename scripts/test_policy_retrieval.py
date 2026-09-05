"""Integration test script for Gemini Policy Retrieval and Grounding.

Tests live retrieval for demo claims CLM-001, CLM-002, and CLM-003.
Requires GEMINI_API_KEY in environment.

Usage:
    python scripts/test_policy_retrieval.py
"""

from __future__ import annotations

import io
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
from src.retrieval.policy_retriever import PolicyRetriever, PolicyRetrieverError

DEMO_DIR = BASE_DIR / "data" / "demo_claims"


def run_policy_retrieval_test() -> int:
    print("=" * 60)
    print("ClaimLens Policy Retrieval Integration Test")
    print("=" * 60)

    if not settings.gemini_configured:
        print("[FAIL] GEMINI_API_KEY is not configured in environment.")
        print("Please set GEMINI_API_KEY to run live policy retrieval integration.")
        return 1

    print(f"Embedding Model: {settings.gemini_embedding_model}")
    print("-" * 60)

    try:
        retriever = PolicyRetriever()
        retriever.ensure_index()
        print(f"[OK] Policy vector index initialized ({len(retriever.index.clauses)} clauses).")
    except Exception as e:
        print(f"[FAIL] Failed to initialize policy retriever: {e}")
        return 1

    cases = [
        ("CLM-001", DEMO_DIR / "claim_001_clean_accident" / "metadata.json"),
        ("CLM-002", DEMO_DIR / "claim_002_contradiction" / "metadata.json"),
        ("CLM-003", DEMO_DIR / "claim_003_missing_fir" / "metadata.json"),
    ]

    all_passed = True

    for claim_id, meta_path in cases:
        print("\n" + "-" * 60)
        print(f"Testing Claim: {claim_id}")
        print("-" * 60)

        if not meta_path.exists():
            print(f"[FAIL] Metadata file missing: {meta_path}")
            all_passed = False
            continue

        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Prepare facts dict
        facts = {
            "claim_id": metadata.get("claim_id"),
            "incident_type": metadata.get("claim_type"),
            "vehicle_registration": metadata.get("vehicle_registration"),
            "incident_date": metadata.get("incident_date"),
            "notification_date": metadata.get("notification_date"),
            "claimed_amount": metadata.get("claimed_amount"),
            "repair_estimate_amount": metadata.get("repair_estimate_amount"),
            "incident_description": metadata.get("incident_description"),
        }

        # For CLM-002 nested claim form values
        if "claim_form" in metadata:
            cf = metadata["claim_form"]
            facts.setdefault("incident_date", cf.get("incident_date"))
            facts.setdefault("notification_date", cf.get("notification_date"))
            facts.setdefault("claimed_amount", cf.get("claimed_amount"))
            facts.setdefault("incident_description", cf.get("incident_description"))

        try:
            query, grounded = retriever.retrieve_relevant_clauses(facts, top_k=5)
            print(f"Semantic Query:\n  \"{query}\"\n")
            print("Retrieved Relevant Clauses:")
            for idx, clause in enumerate(grounded, 1):
                pct = int(round(clause.similarity_score * 100))
                print(f"  {idx}. [Clause {clause.clause_id}] {clause.title} ({clause.section})")
                print(f"     Relevance: {clause.similarity_score:.4f} ({pct}%)")
                print(f"     Reason   : {clause.reason}")
                print(f"     Text     : {clause.text[:80]}...")
            print(f"[OK] {claim_id} retrieval successful ({len(grounded)} clauses retrieved).")
        except PolicyRetrieverError as e:
            print(f"[FAIL] {claim_id} retrieval failed: {e.message}")
            all_passed = False
        except Exception as e:
            print(f"[FAIL] {claim_id} unexpected error: {e}")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("ALL POLICY RETRIEVAL INTEGRATION TESTS PASSED")
        return 0
    else:
        print("SOME INTEGRATION TESTS FAILED")
        return 1


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run_policy_retrieval_test())
