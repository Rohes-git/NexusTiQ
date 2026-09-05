"""ClaimLens — Motor Insurance Claims Evidence Review Assistant.

Entry point. Run with: python app.py
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from typing import Optional
import uvicorn
import logging

# Ensure root .env is loaded safely before accessing settings
from src.config import settings, ROOT_ENV_PATH
from src.extraction.document_loader import (
    DocumentLoader,
    DocumentLoaderError,
    EmptyDocumentError,
    InvalidFileTypeError,
    CorruptedDocumentError,
)
from src.extraction.gemini_extractor import (
    GeminiExtractor,
    GeminiNotConfiguredError,
    GeminiAPIError,
)
from src.models import (
    ClaimSubmission,
    DocumentSummary,
    ExtractionResponse,
    ExtractionError,
    PolicyRetrievalRequest,
)
from src.retrieval.policy_retriever import (
    PolicyRetriever,
    PolicyRetrieverError,
)
from src.retrieval.grounding import (
    PolicyRetrievalResponse,
    GroundedClause,
)

logger = logging.getLogger("claimlens")

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


@app.post("/api/extract-document", response_model=ExtractionResponse)
async def extract_document(file: UploadFile = File(...)):
    """Ingest a single PDF document and extract structured facts with evidence using Gemini."""
    if not file or not file.filename:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(
                code="INVALID_FILE",
                message="No file uploaded or filename missing.",
            ),
        )

    # Check extension
    if not file.filename.lower().endswith(".pdf"):
        return ExtractionResponse(
            success=False,
            error=ExtractionError(
                code="UNSUPPORTED_FILE_TYPE",
                message="Only PDF files are supported.",
            ),
        )

    # Read bytes safely with size limit
    try:
        content_bytes = await file.read()
    except Exception as e:
        logger.error(f"Error reading uploaded file: {e}")
        return ExtractionResponse(
            success=False,
            error=ExtractionError(
                code="READ_ERROR",
                message="Failed to read uploaded file.",
            ),
        )

    if len(content_bytes) > settings.max_upload_size_bytes:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(
                code="FILE_TOO_LARGE",
                message=f"File exceeds maximum allowed size ({settings.max_upload_size_bytes // (1024 * 1024)} MB).",
            ),
        )

    # 1. Local document ingestion & text extraction via PyMuPDF
    try:
        doc_text = DocumentLoader.load_pdf(content_bytes, filename=file.filename)
    except InvalidFileTypeError as e:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(code="INVALID_PDF", message=str(e)),
        )
    except EmptyDocumentError as e:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(code="EMPTY_DOCUMENT", message=str(e)),
        )
    except CorruptedDocumentError as e:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(code="CORRUPTED_PDF", message=str(e)),
        )
    except Exception as e:
        logger.error(f"Unexpected document loader error: {e}")
        return ExtractionResponse(
            success=False,
            error=ExtractionError(code="LOADER_ERROR", message="Failed to process PDF document."),
        )

    # 2. Check Gemini configuration
    if not settings.gemini_configured:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(
                code="GEMINI_UNAVAILABLE",
                message="GEMINI_API_KEY is not configured on the server. Please set the environment variable.",
            ),
        )

    # 3. Structured fact extraction via Gemini
    try:
        extractor = GeminiExtractor()
        doc_type, facts = extractor.extract_facts(doc_text)

        return ExtractionResponse(
            success=True,
            document=DocumentSummary(
                filename=doc_text.filename,
                document_type=doc_type.value,
                page_count=doc_text.total_pages,
            ),
            facts=facts,
        )
    except GeminiNotConfiguredError as e:
        return ExtractionResponse(
            success=False,
            error=ExtractionError(code=e.code, message=e.message),
        )
    except GeminiAPIError as e:
        logger.error(f"Gemini API error: {e.message}")
        return ExtractionResponse(
            success=False,
            error=ExtractionError(code=e.code, message=f"Extraction failed: {e.message}"),
        )
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {e}")
        return ExtractionResponse(
            success=False,
            error=ExtractionError(
                code="EXTRACTION_FAILED",
                message="An error occurred while extracting facts from the document.",
            ),
        )


@app.post("/api/retrieve-policy", response_model=PolicyRetrievalResponse)
async def retrieve_policy(request: PolicyRetrievalRequest):
    """Retrieve and ground relevant policy clauses for extracted claim facts."""
    facts = request.facts if request.facts is not None else request.claim_facts
    if facts is None or (isinstance(facts, list) and len(facts) == 0) or (isinstance(facts, dict) and len(facts) == 0):
        return PolicyRetrievalResponse(
            success=False,
            error="No claim facts provided in request. Please extract or provide facts first.",
        )

    try:
        retriever = PolicyRetriever()
        query, grounded = retriever.retrieve_relevant_clauses(facts, top_k=request.top_k)
        return PolicyRetrievalResponse(
            success=True,
            query=query,
            clauses=grounded,
        )
    except PolicyRetrieverError as e:
        logger.error(f"Policy retriever error: {e.message}")
        return PolicyRetrievalResponse(
            success=False,
            error=f"Retrieval failed ({e.code}): {e.message}",
        )
    except Exception as e:
        logger.error(f"Unexpected error during policy retrieval: {e}")
        return PolicyRetrievalResponse(
            success=False,
            error="An unexpected error occurred during policy clause retrieval.",
        )


@app.post("/api/claims/review")
async def review_claim(
    claim_form: Optional[UploadFile] = File(None),
    repair_estimate: Optional[UploadFile] = File(None),
    incident_description: Optional[str] = Form(""),
    claim_id: Optional[str] = Form(""),
):
    """Accept claim documents for review (placeholder acknowledgment)."""
    received_docs = []
    if claim_form and claim_form.filename:
        received_docs.append({"type": "claim_form", "filename": claim_form.filename})
    if repair_estimate and repair_estimate.filename:
        received_docs.append({"type": "repair_estimate", "filename": repair_estimate.filename})

    return {
        "status": "received",
        "message": "Review engine will be connected in a later milestone.",
        "claim_id": claim_id or None,
        "incident_description_provided": bool(incident_description.strip()),
        "documents_received": received_docs,
    }


# ── Error handling ────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. Please try again."},
    )


# ── Startup ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
