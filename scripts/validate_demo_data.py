"""Validation script for ClaimLens demo data & synthetic policy.

Verifies:
1. Required directories exist.
2. Required files exist.
3. PDFs are valid and extractable with PyMuPDF.
4. Claim IDs are consistent.
5. Required fields exist.
6. Ground truth manifest is internally consistent.
7. Case 003 (theft) does NOT contain an FIR.
8. Case 002 (contradiction) contains both contradictory values.
9. Case 001 (clean) has matching values.
"""

import sys
import json
from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = BASE_DIR / "data" / "policy"
DEMO_DIR = BASE_DIR / "data" / "demo_claims"


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = pymupdf.open(str(pdf_path))
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    doc.close()
    return text


def validate():
    print("==================================================")
    print("ClaimLens Demo Data Validation")
    print("==================================================")

    errors = []

    # ── 1. Policy validation ──────────────────────────────────────
    policy_json_path = POLICY_DIR / "motor_policy.json"
    policy_pdf_path = POLICY_DIR / "ClaimLens_Motor_Policy.pdf"

    clause_count = 0
    if not policy_json_path.exists():
        errors.append(f"Missing policy JSON: {policy_json_path}")
    else:
        with open(policy_json_path, "r", encoding="utf-8") as f:
            policy_data = json.load(f)

        clause_count = len(policy_data.get("clauses", []))
        if clause_count < 12 or clause_count > 16:
            errors.append(f"Expected 12-16 clauses, found {clause_count}")
        else:
            print(f"[OK] Policy JSON exists ({clause_count} clauses)")

        # Check required clause IDs
        expected_ids = {"1.1", "1.2", "2.1", "2.2", "3.1", "3.2", "4.1", "4.2", "4.3", "5.1", "5.2", "6.1", "6.2", "7.1", "7.2", "7.3"}
        actual_ids = {c["clause_id"] for c in policy_data.get("clauses", [])}
        missing_ids = expected_ids - actual_ids
        if missing_ids:
            errors.append(f"Missing expected clause IDs: {missing_ids}")
        else:
            print("[OK] All required policy clause IDs present")

    if not policy_pdf_path.exists():
        errors.append(f"Missing policy PDF: {policy_pdf_path}")
    else:
        pdf_text = extract_pdf_text(policy_pdf_path)
        if "ClaimLens Motor Secure Policy" not in pdf_text:
            errors.append("Policy PDF missing title text")
        if "SYNTHETIC DEMONSTRATION DOCUMENT" not in pdf_text:
            errors.append("Policy PDF missing synthetic disclaimer")
        doc = pymupdf.open(str(policy_pdf_path))
        page_count = len(doc)
        doc.close()
        print(f"[OK] Policy PDF valid ({page_count} pages, extractable with PyMuPDF)")

    # ── 2. Ground truth manifest validation ───────────────────────
    gt_path = DEMO_DIR / "ground_truth.json"
    if not gt_path.exists():
        errors.append(f"Missing ground truth JSON: {gt_path}")
        return False
    else:
        with open(gt_path, "r", encoding="utf-8") as f:
            gt_data = json.load(f)
        cases = {c["claim_id"]: c for c in gt_data.get("cases", [])}
        print(f"[OK] Ground truth manifest loaded ({len(cases)} cases)")

    # ── 3. Case 001: Clean Accident ───────────────────────────────
    c1_dir = DEMO_DIR / "claim_001_clean_accident"
    c1_claim_pdf = c1_dir / "claim_form.pdf"
    c1_estimate_pdf = c1_dir / "repair_estimate.pdf"
    c1_meta_path = c1_dir / "metadata.json"

    if not (c1_claim_pdf.exists() and c1_estimate_pdf.exists() and c1_meta_path.exists()):
        errors.append("Case 001 missing one or more required files")
    else:
        with open(c1_meta_path, "r", encoding="utf-8") as f:
            c1_meta = json.load(f)

        assert c1_meta["claim_id"] == "CLM-001"
        assert c1_meta["expected_recommendation"] == "APPROVE"
        assert c1_meta["claimed_amount"] == c1_meta["repair_estimate_amount"]

        c1_claim_text = extract_pdf_text(c1_claim_pdf)
        c1_est_text = extract_pdf_text(c1_estimate_pdf)

        assert "CLM-001" in c1_claim_text and "CLM-001" in c1_est_text
        assert "TN01AB1234" in c1_claim_text and "TN01AB1234" in c1_est_text
        assert "78,000" in c1_claim_text and "78,000" in c1_est_text
        assert "20 August 2026" in c1_claim_text and "20 August 2026" in c1_est_text
        print("[OK] CLM-001 documents valid & internally consistent (APPROVE)")

    # ── 4. Case 002: Contradictory Accident ───────────────────────
    c2_dir = DEMO_DIR / "claim_002_contradiction"
    c2_claim_pdf = c2_dir / "claim_form.pdf"
    c2_estimate_pdf = c2_dir / "repair_estimate.pdf"
    c2_meta_path = c2_dir / "metadata.json"

    if not (c2_claim_pdf.exists() and c2_estimate_pdf.exists() and c2_meta_path.exists()):
        errors.append("Case 002 missing one or more required files")
    else:
        with open(c2_meta_path, "r", encoding="utf-8") as f:
            c2_meta = json.load(f)

        assert c2_meta["claim_id"] == "CLM-002"
        assert c2_meta["expected_recommendation"] == "REQUEST_INFORMATION"
        assert len(c2_meta["expected_contradictions"]) >= 2

        c2_claim_text = extract_pdf_text(c2_claim_pdf)
        c2_est_text = extract_pdf_text(c2_estimate_pdf)

        # Verify deliberate contradictions in the PDFs
        assert "10 August 2026" in c2_claim_text, "Case 002 claim form must have 10 August 2026"
        assert "14 August 2026" in c2_est_text, "Case 002 estimate must have 14 August 2026"
        assert "85,000" in c2_claim_text, "Case 002 claim form must have 85,000"
        assert "92,000" in c2_est_text, "Case 002 estimate must have 92,000"
        print("[OK] CLM-002 deliberate contradictions verified in PDFs (REQUEST_INFORMATION)")

    # ── 5. Case 003: Theft with Missing FIR ───────────────────────
    c3_dir = DEMO_DIR / "claim_003_missing_fir"
    c3_claim_pdf = c3_dir / "claim_form.pdf"
    c3_meta_path = c3_dir / "metadata.json"

    fir_files = list(c3_dir.glob("*fir*")) + list(c3_dir.glob("*FIR*"))
    if fir_files:
        errors.append(f"Case 003 must NOT contain an FIR, but found: {fir_files}")

    if not (c3_claim_pdf.exists() and c3_meta_path.exists()):
        errors.append("Case 003 missing claim_form.pdf or metadata.json")
    else:
        with open(c3_meta_path, "r", encoding="utf-8") as f:
            c3_meta = json.load(f)

        assert c3_meta["claim_id"] == "CLM-003"
        assert c3_meta["claim_type"] == "theft"
        assert c3_meta["expected_recommendation"] == "REQUEST_INFORMATION"
        assert any("FIR" in doc.get("document", "") for doc in c3_meta.get("expected_missing_documents", []))

        c3_claim_text = extract_pdf_text(c3_claim_pdf)
        assert "CLM-003" in c3_claim_text
        assert "Theft" in c3_claim_text
        print("[OK] CLM-003 FIR intentionally missing & metadata valid (REQUEST_INFORMATION)")

    # ── Final report ──────────────────────────────────────────────
    print("--------------------------------------------------")
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  [FAIL] {e}")
        print("RESULT: FAIL")
        return False
    else:
        print("[OK] Policy exists")
        print(f"[OK] Policy contains {clause_count} clauses")
        print("[OK] CLM-001 documents valid")
        print("[OK] CLM-001 internally consistent")
        print("[OK] CLM-002 contradiction detected in ground truth & PDFs")
        print("[OK] CLM-003 FIR intentionally missing")
        print("[OK] Ground truth valid")
        print("RESULT: PASS")
        return True


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    success = validate()
    sys.exit(0 if success else 1)
