TRACK_ID=PS02

# ClaimLens

**Motor Insurance Claims Evidence Review Assistant**

ClaimLens is an evidence-first review assistant for motor insurance claims involving two-wheelers and cars that are damaged in an accident or stolen. It helps claims investigators systematically verify submitted documents, cross-check facts, evaluate policy coverage, and arrive at evidence-backed recommendations.

> Evidence first. Decisions second.

---

## Current Milestone

**Milestone 4 — Policy Retrieval and Clause Grounding**

This milestone implements semantic policy clause retrieval and factual clause grounding:

- **Policy Clause Indexing**: Loads the 16-clause synthetic motor policy, preserving clause IDs (e.g., `2.1`, `3.2`), section names, titles, and exact clause text, while computing a canonical SHA-256 hash for cache invalidation.
- **Gemini Embeddings & Local Caching**: Uses `google-genai` embedding API (`text-embedding-004`) to generate dense vector embeddings, cached locally at `data/policy/policy_embeddings.json` with hash and model validity checks.
- **Factual Semantic Query Construction**: Converts extracted claim facts (incident type, vehicle details, dates, financial amounts) into targeted search queries without fabricating facts or making premature coverage conclusions.
- **Local Vector Search**: Lightweight NumPy-based cosine similarity index ranking relevant clauses deterministically.
- **Clause Grounding Layer**: Attaches deterministic, factual relevance rationale to each retrieved clause (strictly avoiding approval/rejection or fraud determinations).
- **Interactive UI & API**: Exposes `POST /api/retrieve-policy` and adds interactive policy grounding cards with relevance percentages and exact policy quotes in the frontend.

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
| `GEMINI_EMBEDDING_MODEL` | No (Default: `text-embedding-004`) | Gemini embedding model used for vector retrieval. |

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

## Roadmap

| Milestone | Description | Status |
|---|---|---|
| **1** | Application foundation | Done |
| **2** | Policy and demo data | Done |
| **3** | Document extraction (Gemini) | Done |
| **4** | Evidence retrieval (embeddings + policy search) | Done (Current) |
| **5** | Deterministic policy rules | Next |
| **6** | Contradiction detection | Pending |
| **7** | Review generation (Gemini report) | Pending |
| **8** | Difficult-case testing | Pending |
| **9** | Hackathon hardening | Pending |
