TRACK_ID=PS02

# ClaimLens

**Motor Insurance Claims Evidence Review Assistant**

ClaimLens is an evidence-first review assistant for motor insurance claims involving two-wheelers and cars that are damaged in an accident or stolen. It helps claims investigators systematically verify submitted documents, cross-check facts, evaluate policy coverage, and arrive at evidence-backed recommendations.

> Evidence first. Decisions second.

---

## Current Milestone

**Milestone 2 — Policy and Demo Data**

This milestone adds a high-quality, synthetic motor insurance policy and synthetic claim evidence dataset that serves as ground truth for the review pipeline:

- **Fictional Policy**: 16 clearly numbered clauses across 7 sections covering policy period, accidental damage, theft, exclusions, IDV, claim notification, and required documents. Available as structured JSON (`data/policy/motor_policy.json`) and searchable PDF (`data/policy/ClaimLens_Motor_Policy.pdf`).
- **Demo Claim Dataset**: 3 synthetic claim scenarios exercising key evidence-review states (Supported, Contradictory, Incomplete).
- **Ground Truth Manifest**: `data/demo_claims/ground_truth.json` defining expected recommendations and evidence checks.
- **Validation Suite**: `scripts/validate_demo_data.py` validating PDF integrity, text extraction with PyMuPDF, and ground-truth consistency.

> **Disclaimer**: All policies and claim documents in this repository are completely fictional and synthetic. They do not represent real customers, real insurers, or official insurance contracts.

---

## Synthetic Demo Claims

| Case ID | Scenario | Claim Type | Evidence Documents | Key Review Condition | Expected Recommendation |
|---|---|---|---|---|---|
| **CLM-001** | Clean Accident | Accident | `claim_form.pdf`, `repair_estimate.pdf` | **Supported**: All documents present, facts agree, consistent repair amount (₹78,000), valid dates | `APPROVE` |
| **CLM-002** | Contradictory Accident | Accident | `claim_form.pdf`, `repair_estimate.pdf` | **Contradictory**: Deliberate mismatches — incident date (10 Aug vs 14 Aug) & amount (₹85,000 vs ₹92,000) | `REQUEST_INFORMATION` |
| **CLM-003** | Theft with Missing FIR | Theft | `claim_form.pdf` | **Incomplete**: Mandatory First Information Report (FIR) is missing under Clause 3.2 & 7.2 | `REQUEST_INFORMATION` |

---

## Project Structure

```
app.py                                      # Application entry point
requirements.txt                            # Python dependencies
README.md                                   # This file
.gitignore                                  # Git exclusions

src/
  config.py                                 # Environment configuration
  models.py                                 # Pydantic domain models
  extraction/
    gemini_extractor.py                     # Document extraction (Milestone 3)
  retrieval/
    embeddings.py                           # Embedding service (Milestone 4)
    policy_retriever.py                     # Policy clause retrieval (Milestone 4)
  rules/
    coverage.py                             # Coverage evaluation (Milestone 5)
    documents.py                            # Document completeness (Milestone 5)
    consistency.py                          # Contradiction detection (Milestone 6)
    recommendation.py                       # Recommendation logic (Milestone 5)
  review/
    review_engine.py                        # Review orchestration
  llm/
    report_writer.py                        # Report generation (Milestone 7)

data/
  policy/
    motor_policy.json                       # 16-clause structured policy JSON
    ClaimLens_Motor_Policy.pdf              # Human-readable policy PDF
  demo_claims/
    ground_truth.json                       # Ground truth manifest for all cases
    claim_001_clean_accident/               # Case 001: Clean accident (APPROVE)
      claim_form.pdf
      repair_estimate.pdf
      metadata.json
    claim_002_contradiction/                # Case 002: Contradictory accident (REQUEST_INFORMATION)
      claim_form.pdf
      repair_estimate.pdf
      metadata.json
    claim_003_missing_fir/                  # Case 003: Theft without FIR (REQUEST_INFORMATION)
      claim_form.pdf
      metadata.json

scripts/
  generate_demo_pdfs.py                     # PDF generator script using ReportLab
  validate_demo_data.py                     # Validation script using PyMuPDF

frontend/
  index.html                                # ClaimLens UI
  static/
    styles.css                              # Stylesheet
    app.js                                  # Frontend logic

tests/                                      # Pytest test suite
  test_app.py                               # App and endpoint tests
  test_demo_data.py                         # Policy and demo claim dataset tests
```

---

## Requirements

- Python 3.11+
- No Node.js, npm, or frontend build tools required

### Dependencies

- `fastapi`
- `uvicorn`
- `pydantic`
- `python-multipart`
- `reportlab`
- `pymupdf`

---

## How to Run

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Validate Demo Data & Policy

```bash
python scripts/validate_demo_data.py
```

### 3. Run Application

```bash
python app.py
```

The application starts at: **http://localhost:8000**

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | No (Milestones 1 & 2) | Google Gemini API key. Not used yet — the app starts and runs fully without it. |

Gemini integration will be added in Milestone 3.

---

## Roadmap

| Milestone | Description | Status |
|---|---|---|
| **1** | Application foundation | Done |
| **2** | Policy and demo data | Done (Current) |
| **3** | Document extraction (Gemini) | Next |
| **4** | Evidence retrieval (embeddings + policy search) | Pending |
| **5** | Deterministic policy rules | Pending |
| **6** | Contradiction detection | Pending |
| **7** | Review generation (Gemini report) | Pending |
| **8** | Difficult-case testing | Pending |
| **9** | Hackathon hardening | Pending |
