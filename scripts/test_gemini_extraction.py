"""Integration test script for Gemini Document Fact Extraction.

Tests end-to-end ingestion and Gemini extraction against synthetic demo claims.
If GEMINI_API_KEY is not set, prints an informative message and exits cleanly.
"""

import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=BASE_DIR / ".env", override=False)
except ImportError:
    pass

from src.config import settings
from src.extraction.document_loader import DocumentLoader
from src.extraction.gemini_extractor import GeminiExtractor, GeminiNotConfiguredError


def run_gemini_extraction_test():
    print("==================================================")
    print("ClaimLens — Gemini Fact Extraction Integration Test")
    print("==================================================")

    if not settings.gemini_configured:
        print("[NOTICE] GEMINI_API_KEY is not set in environment.")
        print("Skipping live Gemini API integration call.")
        print("To run with live API:")
        print("  export GEMINI_API_KEY='your_api_key'")
        print("  python scripts/test_gemini_extraction.py")
        print("==================================================")
        return 0

    print(f"[INFO] Using Gemini Model: {settings.gemini_model}")

    test_pdf = BASE_DIR / "data" / "demo_claims" / "claim_001_clean_accident" / "claim_form.pdf"
    if not test_pdf.exists():
        print(f"[ERROR] Test PDF not found: {test_pdf}")
        return 1

    print(f"[INFO] Ingesting document: {test_pdf.name}")
    doc_text = DocumentLoader.load_pdf(test_pdf)
    print(f"[OK] Ingested {doc_text.total_pages} page(s) via PyMuPDF")

    print("[INFO] Calling Gemini for structured fact extraction...")
    try:
        extractor = GeminiExtractor()
        doc_type, facts = extractor.extract_facts(doc_text)

        print("--------------------------------------------------")
        print(f"Document Type Identified: {doc_type.value}")
        print(f"Total Facts Extracted:   {len(facts)}")
        print("--------------------------------------------------")

        all_evidence_valid = True
        for idx, fact in enumerate(facts, 1):
            valid_str = "VALID" if fact.evidence_valid else "INVALID (Hallucinated/Not Found)"
            if not fact.evidence_valid:
                all_evidence_valid = False
            print(f"{idx:2d}. {fact.field_name}:")
            print(f"    Normalized Value: {fact.value}")
            print(f"    Raw Value:        {fact.raw_value}")
            print(f"    Page Number:      {fact.page_number}")
            print(f"    Evidence Quote:   \"{fact.evidence_text}\"")
            print(f"    Confidence:       {fact.confidence * 100:.1f}%")
            print(f"    Evidence Status:  [{valid_str}]")
            print()

        print("--------------------------------------------------")
        if all_evidence_valid:
            print("RESULT: PASS — All extracted facts verified against source PDF.")
        else:
            print("RESULT: WARNING — One or more facts failed source page verification.")
        print("==================================================")
        return 0

    except Exception as e:
        print(f"[ERROR] Extraction failed: {e}")
        return 1


if __name__ == "__main__":
    if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(run_gemini_extraction_test())
