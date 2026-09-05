"""Unit tests for Milestone 2 demo data and synthetic policy."""

import json
from pathlib import Path
import pymupdf

BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_DIR = BASE_DIR / "data" / "policy"
DEMO_DIR = BASE_DIR / "data" / "demo_claims"


def test_policy_json_structure():
    policy_path = POLICY_DIR / "motor_policy.json"
    assert policy_path.exists()
    with open(policy_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["synthetic"] is True
    assert "CMS-DEMO-001" == data["policy_id"]
    assert 12 <= len(data["clauses"]) <= 16

    for clause in data["clauses"]:
        assert "clause_id" in clause
        assert "section" in clause
        assert "title" in clause
        assert "text" in clause
        assert "tags" in clause


def test_policy_pdf_extractable():
    pdf_path = POLICY_DIR / "ClaimLens_Motor_Policy.pdf"
    assert pdf_path.exists()
    doc = pymupdf.open(str(pdf_path))
    assert len(doc) >= 2
    full_text = "".join(page.get_text() for page in doc)
    doc.close()
    assert "ClaimLens Motor Secure Policy" in full_text
    assert "SYNTHETIC DEMONSTRATION DOCUMENT" in full_text


def test_ground_truth_manifest():
    gt_path = DEMO_DIR / "ground_truth.json"
    assert gt_path.exists()
    with open(gt_path, "r", encoding="utf-8") as f:
        gt = json.load(f)

    cases = {c["claim_id"]: c for c in gt["cases"]}
    assert "CLM-001" in cases
    assert "CLM-002" in cases
    assert "CLM-003" in cases

    assert cases["CLM-001"]["expected_recommendation"] == "APPROVE"
    assert cases["CLM-002"]["expected_recommendation"] == "REQUEST_INFORMATION"
    assert cases["CLM-003"]["expected_recommendation"] == "REQUEST_INFORMATION"


def test_claim_001_clean_accident():
    c1_dir = DEMO_DIR / "claim_001_clean_accident"
    claim_pdf = c1_dir / "claim_form.pdf"
    est_pdf = c1_dir / "repair_estimate.pdf"
    meta_json = c1_dir / "metadata.json"

    assert claim_pdf.exists() and est_pdf.exists() and meta_json.exists()

    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["expected_recommendation"] == "APPROVE"
    assert meta["claimed_amount"] == meta["repair_estimate_amount"]


def test_claim_002_contradictions():
    c2_dir = DEMO_DIR / "claim_002_contradiction"
    claim_pdf = c2_dir / "claim_form.pdf"
    est_pdf = c2_dir / "repair_estimate.pdf"
    meta_json = c2_dir / "metadata.json"

    assert claim_pdf.exists() and est_pdf.exists() and meta_json.exists()

    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["expected_recommendation"] == "REQUEST_INFORMATION"
    assert len(meta["expected_contradictions"]) >= 2


def test_claim_003_missing_fir():
    c3_dir = DEMO_DIR / "claim_003_missing_fir"
    claim_pdf = c3_dir / "claim_form.pdf"
    meta_json = c3_dir / "metadata.json"

    assert claim_pdf.exists() and meta_json.exists()
    # Ensure no FIR file exists
    fir_files = list(c3_dir.glob("*fir*")) + list(c3_dir.glob("*FIR*"))
    assert len(fir_files) == 0

    with open(meta_json, "r", encoding="utf-8") as f:
        meta = json.load(f)
    assert meta["expected_recommendation"] == "REQUEST_INFORMATION"
    assert meta["claim_type"] == "theft"
    assert any("FIR" in doc.get("document", "") for doc in meta.get("expected_missing_documents", []))
