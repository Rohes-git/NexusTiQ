TRACK_ID=PS02

# ClaimLens

**Motor Insurance Claims Evidence Review Assistant**

ClaimLens is an evidence-first review assistant for motor insurance claims involving two-wheelers and cars that are damaged in an accident or stolen. It helps claims investigators systematically verify submitted documents, cross-check facts, evaluate policy coverage, and arrive at evidence-backed recommendations.

> Evidence first. Decisions second.

---

## Current Milestone

**Milestone 3 — Document Ingestion and Fact Extraction**

This milestone implements the core document processing OCR and fact extraction pipeline:

- **Page-Aware PDF Ingestion**: Extracts text from PDFs page-by-page using `PyMuPDF`, maintaining structural delimiters (`--- PAGE X ---`) to guarantee precise provenance tracking.
- **Structured Fact Extraction**: Leverages the official `google-genai` SDK to extract domain-specific entities (amounts, dates, vehicle details) using Pydantic `GeminiExtractionSchema` and deterministic temperature `0.0`.
- **Python-Side Evidence Verification**: Prevents AI hallucination through deterministic validation (`verify_evidence_in_page`) that ensures requested `evidence_text` quotes actually appear in the source page text.
- **Deterministic Normalization**: Standardizes currency amounts (e.g., `"Rs. 72,000/-"` → `72000`) and date formats (e.g., `"20 August 2026"` → `"2026-08-20"`) without losing the raw extracted values or context.
- **Robust Endpoint API**: Extends `GET /api/health` and implements `POST /api/extract-document` with local fallbacks, mock testing offline fixtures (`tests/fixtures/`), and frontend evidence component visualization (`index.html`).

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
| `GEMINI_API_KEY` | Optional for running/testing offline (Required for live Gemini extraction) | Google Gemini API key. If unset, unit tests run against offline fixtures and the API gracefully reports `GEMINI_UNAVAILABLE`. |
| `GEMINI_MODEL` | No (Default: `gemini-2.0-flash`) | Gemini model identifier used for extraction. |

---

## Roadmap

| Milestone | Description | Status |
|---|---|---|
| **1** | Application foundation | Done |
| **2** | Policy and demo data | Done |
| **3** | Document extraction (Gemini) | Done (Current) |
| **4** | Evidence retrieval (embeddings + policy search) | Next |
| **5** | Deterministic policy rules | Pending |
| **6** | Contradiction detection | Pending |
| **7** | Review generation (Gemini report) | Pending |
| **8** | Difficult-case testing | Pending |
| **9** | Hackathon hardening | Pending |
