"""Gemini-based structured document fact extraction.

Uses the official Google GenAI SDK (google-genai) to extract structured
facts from page-aware PDF text. Every fact is paired with exact supporting
evidence and validated against the source page text in Python.
"""

import json
import re
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from src.config import settings
from src.models import (
    Document,
    ClaimFacts,
    DocumentText,
    DocumentType,
    ExtractedFact,
    GeminiExtractionSchema,
    RawFactItem,
    normalize_amount,
    normalize_date,
)


EXTRACTION_SYSTEM_INSTRUCTION = """You are a document fact extraction system for a motor insurance claims review application.

Your task is to extract ONLY information explicitly present in the supplied document.

Rules:
1. Never infer missing information.
2. Never resolve contradictions.
3. Never choose between conflicting values.
4. Never invent dates, amounts, names or identifiers.
5. If a field is absent, return null.
6. If the document contains conflicting values, preserve the value appearing in the current document and provide evidence for it.
7. Every extracted fact must include the exact supporting text (short quote) and page number.
8. Identify the document type from its content ('claim_form', 'repair_estimate', 'fir', or 'unknown').
9. Do not make coverage decisions.
10. Do not make claim approval/rejection decisions.
11. Do not infer facts from filenames.

Extract facts strictly according to the provided schema.
"""


class GeminiExtractorError(Exception):
    """Base exception for Gemini extraction errors."""
    def __init__(self, message: str, code: str = "EXTRACTION_ERROR"):
        super().__init__(message)
        self.code = code
        self.message = message


class GeminiNotConfiguredError(GeminiExtractorError):
    """Raised when GEMINI_API_KEY is not set."""
    def __init__(self, message: str = "GEMINI_API_KEY is not configured in the environment."):
        super().__init__(message, code="GEMINI_NOT_CONFIGURED")


class GeminiAPIError(GeminiExtractorError):
    """Raised when Gemini API call fails."""
    def __init__(self, message: str):
        super().__init__(message, code="GEMINI_API_ERROR")


def verify_evidence_in_page(evidence_text: Optional[str], page_text: Optional[str]) -> bool:
    """Validate that evidence text actually appears on the claimed page.

    Performs safe whitespace normalization to account for line breaks and spacing.
    """
    if not evidence_text or not page_text:
        return False

    ev_norm = re.sub(r"\s+", " ", evidence_text).strip().lower()
    page_norm = re.sub(r"\s+", " ", page_text).strip().lower()

    if not ev_norm:
        return False

    return ev_norm in page_norm


class GeminiExtractor:
    """Extracts structured facts from page-aware document text using Gemini."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.gemini_api_key
        self.model = model if model is not None else settings.gemini_model
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise GeminiNotConfiguredError()
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def extract_facts(self, doc_text: DocumentText) -> tuple[DocumentType, list[ExtractedFact]]:
        """Extract structured facts from page-aware document text.

        Args:
            doc_text: Structured DocumentText with page-by-page text.

        Returns:
            Tuple of (classified DocumentType, list of validated ExtractedFact).

        Raises:
            GeminiNotConfiguredError: If API key is missing.
            GeminiAPIError: If API call or parsing fails.
        """
        client = self._get_client()
        content_prompt = (
            f"Document Filename: {doc_text.filename}\n"
            f"Total Pages: {doc_text.total_pages}\n\n"
            f"Content:\n{doc_text.get_page_aware_text()}"
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=content_prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiExtractionSchema,
                    system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                    temperature=0.0,
                ),
            )

            response_text = response.text
            if not response_text:
                raise GeminiAPIError("Gemini returned an empty response.")

            parsed_data = json.loads(response_text)
            raw_schema = GeminiExtractionSchema.model_validate(parsed_data)

        except APIError as e:
            raise GeminiAPIError(f"Gemini API error: {str(e)}") from e
        except json.JSONDecodeError as e:
            raise GeminiAPIError(f"Failed to parse Gemini structured JSON: {str(e)}") from e
        except Exception as e:
            raise GeminiAPIError(f"Extraction failed: {str(e)}") from e

        return self.process_raw_schema(raw_schema, doc_text)

    def process_raw_schema(
        self,
        schema: GeminiExtractionSchema,
        doc_text: DocumentText,
    ) -> tuple[DocumentType, list[ExtractedFact]]:
        """Process structured Gemini output into validated ExtractedFact items.

        Separated from extract_facts to allow deterministic offline testing with fixtures.
        """
        # 1. Determine document type
        doc_type_str = (schema.document_type or "").lower().strip()
        doc_type_map = {
            "claim_form": DocumentType.CLAIM_FORM,
            "repair_estimate": DocumentType.REPAIR_ESTIMATE,
            "fir": DocumentType.FIR,
        }
        classified_type = doc_type_map.get(doc_type_str, DocumentType.UNKNOWN)

        # 2. Extract and validate fields
        field_mappings = [
            ("claim_id", schema.claim_id, "string"),
            ("policy_number", schema.policy_number, "string"),
            ("vehicle_registration", schema.vehicle_registration, "string"),
            ("vehicle_make", schema.vehicle_make, "string"),
            ("vehicle_model", schema.vehicle_model, "string"),
            ("incident_type", schema.incident_type, "string"),
            ("incident_date", schema.incident_date, "date"),
            ("notification_date", schema.notification_date, "date"),
            ("incident_description", schema.incident_description, "string"),
            ("claimed_amount", schema.claimed_amount, "amount"),
            ("repair_estimate_amount", schema.repair_estimate_amount, "amount"),
        ]

        extracted_facts: list[ExtractedFact] = []

        for field_name, fact_item, field_kind in field_mappings:
            if fact_item is None or fact_item.raw_value is None or not str(fact_item.raw_value).strip():
                continue

            raw_val = str(fact_item.raw_value).strip()
            ev_text = (fact_item.evidence_text or "").strip()
            page_num = fact_item.page_number if fact_item.page_number is not None else 1
            conf = fact_item.confidence if fact_item.confidence is not None else 1.0

            # Page range check
            page_in_range = 1 <= page_num <= doc_text.total_pages
            page_text = doc_text.get_page_text(page_num) if page_in_range else None

            # Evidence quotation check
            evidence_valid = page_in_range and verify_evidence_in_page(ev_text, page_text)

            # Normalization
            if field_kind == "amount":
                normalized_val = normalize_amount(raw_val)
            elif field_kind == "date":
                normalized_val = normalize_date(raw_val)
            else:
                normalized_val = raw_val

            extracted_facts.append(ExtractedFact(
                field_name=field_name,
                value=normalized_val,
                raw_value=raw_val,
                evidence_text=ev_text,
                page_number=page_num,
                confidence=conf,
                evidence_valid=evidence_valid,
            ))

        return classified_type, extracted_facts

    def extract_claim_facts(self, document: Document) -> ClaimFacts:
        """Pipeline extraction method (placeholder for Milestone 5 claim facts assembly)."""
        raise NotImplementedError(
            "ClaimFacts pipeline mapping will be implemented in Milestone 5."
        )
