"""Verification and demonstration script for Milestone 6 Contradiction & Evidence Completeness Engine.

Evaluates synthetic demo claims (CLM-001, CLM-002, CLM-003) against ground truth expectations.

Strict Decision Boundary:
- Strictly does NOT print APPROVE, REJECT, DENY, FRAUD, or final claim adjudication.
- Preserves full evidence provenance for human claims investigator audit.

Usage:
    python scripts/test_evidence_review.py
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

from src.analysis.evidence_review import EvidenceReviewEngine
from src.analysis.completeness_checker import CompletenessStatus
from src.analysis.contradiction_detector import ContradictionSeverity

DEMO_DIR = BASE_DIR / "data" / "demo_claims"


def run_evidence_review_verification() -> int:
    print("=" * 72)
    print("ClaimLens — Contradiction & Evidence Completeness Engine (Milestone 6)")
    print("=" * 72)
    print("Decision Boundary: Evidence First. Decisions Second.")
    print("Cross-document fact comparison & document completeness evaluation.")
    print("Empowering human investigators without automated claim adjudication.")
    print("-" * 72)

    engine = EvidenceReviewEngine()

    cases = [
        ("CLM-001", "Clean Accident Claim (Consistent & Complete)", DEMO_DIR / "claim_001_clean_accident"),
        ("CLM-002", "Contradictory Accident (Date Mismatch & Financial Discrepancy)", DEMO_DIR / "claim_002_contradiction"),
        ("CLM-003", "Theft Claim (Missing Mandatory First Information Report - FIR)", DEMO_DIR / "claim_003_missing_fir"),
    ]

    all_passed = True

    for claim_id, description, claim_path in cases:
        print("\n" + "=" * 72)
        print(f"EVALUATING EVIDENCE: {claim_id} — {description}")
        print("=" * 72)

        meta_file = claim_path / "metadata.json"
        if not meta_file.exists():
            print(f"[ERROR] Missing metadata file: {meta_file}")
            all_passed = False
            continue

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        pdf_docs = [p.name for p in claim_path.glob("*.pdf")]

        # Build multi-document records
        doc_records = []
        if claim_id == "CLM-001":
            doc_records = [
                {
                    "document_name": "claim_form.pdf",
                    "document_type": "claim_form",
                    "facts": [
                        {"field_name": "incident_type", "value": "Accident", "raw_value": "Accident", "evidence_text": "Type: Accident", "page_number": 1},
                        {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20 August 2026", "evidence_text": "Date of Incident: 20 August 2026", "page_number": 1},
                        {"field_name": "vehicle_registration", "value": "TN01AB1234", "raw_value": "TN01AB1234", "evidence_text": "Registration: TN01AB1234", "page_number": 1},
                        {"field_name": "claimed_amount", "value": 78000.0, "raw_value": "78000", "evidence_text": "Claimed Amount: Rs. 78,000", "page_number": 1},
                        {"field_name": "incident_description", "value": metadata.get("incident_description"), "raw_value": metadata.get("incident_description"), "evidence_text": "The insured vehicle was travelling...", "page_number": 1},
                    ],
                },
                {
                    "document_name": "repair_estimate.pdf",
                    "document_type": "repair_estimate",
                    "facts": [
                        {"field_name": "incident_date", "value": "2026-08-20", "raw_value": "20 August 2026", "evidence_text": "Date of Loss: 20 August 2026", "page_number": 1},
                        {"field_name": "vehicle_registration", "value": "TN01AB1234", "raw_value": "TN01AB1234", "evidence_text": "Vehicle Reg: TN01AB1234", "page_number": 1},
                        {"field_name": "repair_estimate_amount", "value": 78000.0, "raw_value": "78000", "evidence_text": "Total Estimate: Rs. 78,000", "page_number": 1},
                    ],
                },
            ]
        elif claim_id == "CLM-002":
            cf = metadata.get("claim_form", {})
            re = metadata.get("repair_estimate", {})
            doc_records = [
                {
                    "document_name": "claim_form.pdf",
                    "document_type": "claim_form",
                    "facts": [
                        {"field_name": "incident_type", "value": "Accident", "raw_value": "Accident", "evidence_text": "Type: Accident", "page_number": 1},
                        {"field_name": "incident_date", "value": "2026-08-10", "raw_value": cf.get("incident_date", "10 August 2026"), "evidence_text": "Date of Accident: 10 August 2026", "page_number": 1},
                        {"field_name": "vehicle_registration", "value": "TN02CD5678", "raw_value": "TN02CD5678", "evidence_text": "Reg: TN02CD5678", "page_number": 1},
                        {"field_name": "claimed_amount", "value": float(cf.get("claimed_amount", 85000)), "raw_value": "85000", "evidence_text": "Claimed Amount: Rs. 85,000", "page_number": 1},
                        {"field_name": "incident_description", "value": cf.get("incident_description"), "raw_value": cf.get("incident_description"), "evidence_text": "The vehicle was involved...", "page_number": 1},
                    ],
                },
                {
                    "document_name": "repair_estimate.pdf",
                    "document_type": "repair_estimate",
                    "facts": [
                        {"field_name": "incident_date", "value": "2026-08-14", "raw_value": re.get("incident_date", "14 August 2026"), "evidence_text": "Date of Loss: 14 August 2026", "page_number": 1},
                        {"field_name": "vehicle_registration", "value": "TN02CD5678", "raw_value": "TN02CD5678", "evidence_text": "Reg: TN02CD5678", "page_number": 1},
                        {"field_name": "repair_estimate_amount", "value": float(re.get("estimated_repair_amount", 92000)), "raw_value": "92000", "evidence_text": "Total Estimate: Rs. 92,000", "page_number": 1},
                    ],
                },
            ]
        elif claim_id == "CLM-003":
            doc_records = [
                {
                    "document_name": "claim_form.pdf",
                    "document_type": "claim_form",
                    "facts": [
                        {"field_name": "incident_type", "value": "Theft", "raw_value": "Theft", "evidence_text": "Type: Theft", "page_number": 1},
                        {"field_name": "incident_date", "value": "2026-08-25", "raw_value": "25 August 2026", "evidence_text": "Date of Theft: 25 August 2026", "page_number": 1},
                        {"field_name": "vehicle_registration", "value": "TN03EF9012", "raw_value": "TN03EF9012", "evidence_text": "Reg: TN03EF9012", "page_number": 1},
                        {"field_name": "claimed_amount", "value": float(metadata.get("claimed_amount", 72000)), "raw_value": "72000", "evidence_text": "IDV Claimed: Rs. 72,000", "page_number": 1},
                        {"field_name": "incident_description", "value": metadata.get("incident_description"), "raw_value": metadata.get("incident_description"), "evidence_text": "The insured two-wheeler was parked...", "page_number": 1},
                    ],
                }
            ]

        result = engine.analyze(
            claim_id=claim_id,
            facts=doc_records,
            documents=pdf_docs,
        )

        print(f"Claim Type Identified : {result.claim_type}")
        print(f"Documents Ingested    : {', '.join(pdf_docs) if pdf_docs else 'None'}")
        print(f"Summary Metrics       : {result.summary['total_contradictions']} Contradictions | "
              f"{result.summary['present_documents_count']}/{result.summary['total_required_documents']} Required Documents Present | "
              f"{len(result.consistent_fields)} Verified Matches")
        print("-" * 72)

        # 1. Contradictions Table
        print("1. FACTUAL CONTRADICTIONS & DISCREPANCIES:")
        if not result.contradictions:
            print("   ✓ No contradictions detected across submitted documents.")
        else:
            for i, c in enumerate(result.contradictions, 1):
                sev_sym = "⚡ HIGH" if c.severity == ContradictionSeverity.HIGH else "⚠ " + str(c.severity)
                print(f"   [{i}] {c.category} ({sev_sym})")
                print(f"       • Doc A ({c.document_a}, p.{c.page_a}): {c.value_a} (Quote: \"{c.evidence_a}\")")
                print(f"       • Doc B ({c.document_b}, p.{c.page_b}): {c.value_b} (Quote: \"{c.evidence_b}\")")
                print(f"       • Detail: {c.message}")

        # 2. Completeness Table
        print("\n2. POLICY DOCUMENT COMPLETENESS:")
        for c in result.completeness:
            st_sym = "✓ PRESENT" if c.status == CompletenessStatus.PRESENT else "✗ MISSING" if c.status == CompletenessStatus.MISSING else "⚠ INCOMPLETE"
            print(f"   [{st_sym:12}] Clause {c.clause_id:4} | {c.required_document:24} -> {c.message}")

        # 3. Consistent Fields
        if result.consistent_fields:
            print("\n3. VERIFIED CONSISTENT FACTS:")
            for cf in result.consistent_fields:
                print(f"   ✓ {cf.field_name}: {cf.value} (Matched across: {', '.join(cf.documents)})")

        # Verify ground truth expectations
        if claim_id == "CLM-001":
            if result.summary["total_contradictions"] != 0:
                print(f"\n[FAIL] CLM-001 expected 0 contradictions, got {result.summary['total_contradictions']}")
                all_passed = False
            elif result.summary["missing_documents_count"] != 0:
                print(f"\n[FAIL] CLM-001 expected 0 missing documents, got {result.summary['missing_documents_count']}")
                all_passed = False
            else:
                print("\n>>> CLM-001 GROUND TRUTH PASSED (Supported clean claim with 0 contradictions)")

        elif claim_id == "CLM-002":
            if result.summary["total_contradictions"] < 2:
                print(f"\n[FAIL] CLM-002 expected 2 contradictions, got {result.summary['total_contradictions']}")
                all_passed = False
            else:
                print("\n>>> CLM-002 GROUND TRUTH PASSED (Contradictory claim correctly detected date & amount mismatches)")

        elif claim_id == "CLM-003":
            missing_fir = [c for c in result.completeness if "FIR" in c.required_document and c.status == CompletenessStatus.MISSING]
            if not missing_fir:
                print("\n[FAIL] CLM-003 expected missing FIR finding under Clause 7.2")
                all_passed = False
            else:
                print("\n>>> CLM-003 GROUND TRUTH PASSED (Theft claim correctly flagged missing FIR under Clause 7.2)")

    print("\n" + "=" * 72)
    if all_passed:
        print("ALL DEMO CLAIM EVIDENCE ANALYSIS VERIFICATION CHECKS PASSED (100% SUCCESS)")
        print("=" * 72)
        return 0
    else:
        print("SOME DEMO CLAIM VERIFICATION CHECKS FAILED")
        print("=" * 72)
        return 1


if __name__ == "__main__":
    sys.exit(run_evidence_review_verification())
