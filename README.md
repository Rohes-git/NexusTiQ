TRACK_ID=PS02

# ClaimLens

**Motor Insurance Claims Evidence Review Assistant**

ClaimLens is an evidence-first review assistant for motor insurance claims involving two-wheelers and cars that are damaged in an accident or stolen. It helps claims investigators systematically verify submitted documents, cross-check facts, evaluate policy coverage, and arrive at evidence-backed recommendations.

> Evidence first. Decisions second.

---

## Current Milestone

**Milestone 1 — Application Foundation**

This milestone establishes the clean application skeleton:

- FastAPI backend serving a polished frontend
- Pydantic domain models for claims, documents, evidence, findings, and review results
- Placeholder service interfaces for extraction, retrieval, rules, and report generation
- No AI calls, no external APIs, no fake data

The review engine is **not connected yet**. Submitting a claim shows a placeholder acknowledgment.

---

## Project Structure

```
app.py                          # Application entry point
requirements.txt                # Python dependencies
README.md                       # This file

src/
  config.py                     # Environment configuration
  models.py                     # Pydantic domain models
  extraction/
    gemini_extractor.py         # Document extraction (Milestone 3)
  retrieval/
    embeddings.py               # Embedding service (Milestone 4)
    policy_retriever.py         # Policy clause retrieval (Milestone 4)
  rules/
    coverage.py                 # Coverage evaluation (Milestone 5)
    documents.py                # Document completeness (Milestone 5)
    consistency.py              # Contradiction detection (Milestone 6)
    recommendation.py           # Recommendation logic (Milestone 5)
  review/
    review_engine.py            # Review orchestration
  llm/
    report_writer.py            # Report generation (Milestone 7)

data/
  policy/                       # Policy documents (Milestone 2)
  demo_claims/                  # Demo claim PDFs (Milestone 2)

frontend/
  index.html                    # ClaimLens UI
  static/
    styles.css                  # Stylesheet
    app.js                      # Frontend logic

tests/                          # Test suite
```

---

## Requirements

- Python 3.11+
- No Node.js, npm, or frontend build tools required

### Dependencies

- fastapi
- uvicorn
- pydantic
- python-multipart

---

## How to Run

```bash
pip install -r requirements.txt
python app.py
```

The application starts at: **http://localhost:8000**

No second terminal, no build step, no Docker, no database setup required.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | No (Milestone 1) | Google Gemini API key. Not used yet — the app starts and runs fully without it. |

Gemini integration will be added in Milestone 3.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve the ClaimLens frontend |
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/api/claims/review` | Submit claim documents (placeholder in M1) |

---

## Roadmap

| Milestone | Description |
|---|---|
| **1** | Application foundation ← current |
| **2** | Policy and demo data |
| **3** | Document extraction (Gemini) |
| **4** | Evidence retrieval (embeddings + policy search) |
| **5** | Deterministic policy rules |
| **6** | Contradiction detection |
| **7** | Review generation (Gemini report) |
| **8** | Difficult-case testing |
| **9** | Hackathon hardening |

---

## What Is Not Implemented Yet

- Gemini API calls
- PDF text extraction
- Policy document retrieval
- Coverage / consistency / recommendation rules
- Report generation
- Authentication
- Cloud deployment
- Fraud detection

These are intentionally deferred to later milestones.
