"""Document Ingestion Service.

Extracts text from PDF documents page by page using PyMuPDF.
Preserves page-level provenance required for evidence validation.
"""

from pathlib import Path
from typing import Union
import pymupdf

from src.models import DocumentText, DocumentPage, DocumentType


class DocumentLoaderError(Exception):
    """Base exception for document loading errors."""
    pass


class InvalidFileTypeError(DocumentLoaderError):
    """Raised when an uploaded file is not a valid PDF."""
    pass


class EmptyDocumentError(DocumentLoaderError):
    """Raised when a PDF contains no pages or extractable text."""
    pass


class CorruptedDocumentError(DocumentLoaderError):
    """Raised when a PDF file is corrupt or unreadable."""
    pass


class DocumentLoader:
    """Loads and extracts text page-by-page from PDF files."""

    @staticmethod
    def load_pdf(source: Union[str, Path, bytes], filename: str = "document.pdf") -> DocumentText:
        """Extract page-aware text from a PDF file path or raw bytes.

        Args:
            source: Path to the PDF file or raw PDF bytes.
            filename: Display filename for metadata tracking.

        Returns:
            DocumentText containing structured page-by-page text.

        Raises:
            FileNotFoundError: If source path does not exist.
            InvalidFileTypeError: If source is not a PDF.
            CorruptedDocumentError: If PDF cannot be parsed.
            EmptyDocumentError: If PDF contains no extractable text.
        """
        doc = None
        try:
            if isinstance(source, (str, Path)):
                path = Path(source)
                if not path.exists():
                    raise FileNotFoundError(f"File not found: {path}")
                if path.suffix.lower() != ".pdf":
                    raise InvalidFileTypeError(f"Unsupported file format: {path.suffix}. Only PDF is supported.")
                filename = path.name
                doc = pymupdf.open(str(path))
            elif isinstance(source, bytes):
                if not source.startswith(b"%PDF"):
                    raise InvalidFileTypeError("Provided data does not match PDF file signature.")
                doc = pymupdf.open(stream=source, filetype="pdf")
            else:
                raise ValueError("Source must be a file path (str/Path) or bytes.")

            if len(doc) == 0:
                raise EmptyDocumentError("PDF document contains no pages.")

            pages: list[DocumentPage] = []
            total_chars = 0

            for page_idx in range(len(doc)):
                page = doc[page_idx]
                page_text = page.get_text() or ""
                total_chars += len(page_text.strip())
                pages.append(DocumentPage(
                    page_number=page_idx + 1,
                    text=page_text,
                ))

            if total_chars == 0:
                raise EmptyDocumentError("Document contains no extractable text.")

            return DocumentText(
                filename=filename,
                document_type=DocumentType.UNKNOWN,
                pages=pages,
                total_pages=len(pages),
            )

        except (DocumentLoaderError, FileNotFoundError):
            raise
        except Exception as e:
            raise CorruptedDocumentError(f"Failed to process PDF document: {str(e)}") from e
        finally:
            if doc is not None:
                doc.close()
