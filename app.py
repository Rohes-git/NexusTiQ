"""ClaimLens — Motor Insurance Claims Evidence Review Assistant.

Entry point. Run with: python app.py
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional
import uvicorn

from src.config import settings
from src.models import ClaimSubmission

app = FastAPI(
    title="ClaimLens",
    description="Motor Insurance Claims Evidence Review Assistant — PS02",
    version="0.1.0",
)

# ── Static files & frontend ──────────────────────────────────────────────

FRONTEND_DIR = Path(__file__).parent / "frontend"

app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")


@app.get("/")
async def serve_frontend():
    """Serve the main ClaimLens UI."""
    return FileResponse(FRONTEND_DIR / "index.html")


# ── API routes ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.post("/api/claims/review")
async def review_claim(
    claim_form: Optional[UploadFile] = File(None),
    repair_estimate: Optional[UploadFile] = File(None),
    incident_description: Optional[str] = Form(""),
    claim_id: Optional[str] = Form(""),
):
    """Accept claim documents for review.

    In Milestone 1 this returns a placeholder acknowledging receipt.
    Actual extraction and review will be connected in later milestones.
    """
    received_docs = []
    if claim_form and claim_form.filename:
        received_docs.append({"type": "claim_form", "filename": claim_form.filename})
    if repair_estimate and repair_estimate.filename:
        received_docs.append({"type": "repair_estimate", "filename": repair_estimate.filename})

    return {
        "status": "received",
        "message": "Review engine will be connected in the next milestone.",
        "claim_id": claim_id or None,
        "incident_description_provided": bool(incident_description.strip()),
        "documents_received": received_docs,
    }


# ── Error handling ────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Startup ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
