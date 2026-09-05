TRACK_ID=PS02

# ClaimLens

**Motor Insurance Claims Evidence Review Assistant**

ClaimLens is an evidence-first review assistant for motor insurance claims involving two-wheelers and cars that are damaged in an accident or stolen. It helps claims investigators systematically verify submitted documents, cross-check facts, evaluate policy coverage, and arrive at evidence-backed recommendations.

> Evidence first. Decisions second.

---

## Current Milestone

**Milestone 5 — Deterministic Policy Rule Engine**

This milestone implements deterministic, auditable policy rule evaluations strictly adhering to the 16-clause canonical synthetic motor policy:

- **100% Deterministic Rule Engine**: Evaluates extracted claim facts and document inventories against explicit clauses in `data/policy/motor_policy.json` with zero external API dependencies.
- **Strict Decision Boundary**: Adheres strictly to the *Evidence First, Decisions Second* principle. Allowed finding statuses are `PASS`, `FAIL`, `WARNING`, `INSUFFICIENT_EVIDENCE`, and `NOT_APPLICABLE`. Never outputs premature approval/rejection decisions or fraud claims.
- **Auditable Policy Findings**: Captures `rule_id`, `clause_id`, `category`, `status`, `title`, `message`, `facts_used` (with field values and evidence quotes), `evidence_references`, and `severity`.
- **Policy Rules Implemented**:
  - *Coverage Period (Clause 1.1)*: Verifies incident date falls within active policy dates.
  - *Covered Vehicle (Clause 1.2)*: Confirms registration number and vehicle identification.
  - *Accidental Damage & Repair (Clauses 2.1 & 2.2)*: Evaluates accident coverage eligibility and itemized repair estimates.
  - *Theft Coverage & FIR (Clauses 3.1 & 3.2)*: Validates total loss theft coverage and enforces mandatory First Information Report (FIR) presence.
  - *Valuation & IDV Limits (Clauses 5.1 & 5.2)*: Checks financial claim amounts against IDV caps without premature deduction calculations.
  - *Notification Window (Clauses 6.1 & 6.2)*: Verifies notification timeline ($\le 7$ days $\rightarrow$ `PASS`, $> 7$ days $\rightarrow$ `WARNING` for investigator review).
  - *Required Document Inventories (Clauses 7.1 & 7.2)*: Enforces document completeness for accident claims (Claim Form, Repair Estimate) and theft claims (Claim Form, FIR).
  - *Explicit Exclusions (Clauses 4.1, 4.2, 4.3)*: Evaluates deliberate damage, excluded usage (racing/commercial hire), and misrepresentation.
- **API & Interactive UI**: Exposes `POST /api/evaluate-policy` and adds interactive policy findings cards with color-coded status badges, metrics summary, and non-adjudication disclaimers in the frontend.

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
    policy_retriever.py                     # Policy retrieve orchestration
    policy_loader.py                        # Load canonical policy JSON
    embedding_service.py                    # Gemini embeddings generator
    vector_index.py                         # Local NumPy-based vector index
    query_builder.py                        # Semantic search query constructor
    grounding.py                            # Factual clause grounding
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
  test_gemini_extraction.py                 # Extractor integration test
  build_policy_embeddings.py                # Create/cache embeddings locally
  test_policy_retrieval.py                  # Retriever integration test

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
- `python-dotenv`
- `reportlab`
- `pymupdf`
- `google-genai`
- `numpy`

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
| `GEMINI_EMBEDDING_MODEL` | No (Default: `gemini-embedding-2`) | Gemini embedding model used for vector retrieval. |

---

## Building Policy Embeddings

Live semantic retrieval requires vector embeddings of the policy clauses. You only need to build this index once (or when the policy changes).

If `GEMINI_API_KEY` is exported, run:

```bash
python scripts/build_policy_embeddings.py
```

This will cache a NumPy-compatible JSON index at `data/policy/policy_embeddings.json`. Unit tests use deterministic mock embeddings and do not require this. To test live integration against demo claims safely:

```bash
python scripts/test_policy_retrieval.py
```

---

## Evaluating Policy Rules

You can run deterministic policy rule evaluations on the synthetic demo claims:

```bash
python scripts/test_policy_rules.py
```

This runs offline rule evaluation across all demo cases without requiring network access or API keys.

---

## Roadmap

| Milestone | Description | Status |
|---|---|---|
| **1** | Application foundation | Done |
| **2** | Policy and demo data | Done |
| **3** | Document extraction (Gemini) | Done |
| **4** | Evidence retrieval (embeddings + policy search) | Done |
| **5** | Deterministic policy rules | Done (Current) |
| **6** | Contradiction detection | Next |
| **7** | Review generation (Gemini report) | Pending |
| **8** | Difficult-case testing | Pending |
| **9** | Hackathon hardening | Pending |
