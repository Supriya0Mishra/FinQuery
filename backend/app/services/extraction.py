"""PDF text extraction and LLM structured extraction."""

from dataclasses import dataclass
from io import BytesIO

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pypdf import PdfReader

from app.core.config import get_settings
from app.schemas.extraction import ExtractedInvoice


class ExtractionError(Exception):
    """A document that can never be processed as-is (retrying will not help)."""


@dataclass
class PdfText:
    text: str
    page_count: int


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a precise financial document parser. Extract structured fields from "
            "the document. Copy values EXACTLY as they appear - do not reformat numbers, "
            "dates, or currencies. Be especially careful with Indian number formats like "
            "1,58,415.00 (do not truncate at commas). Extract ALL line items you find. "
            "If a field is not present, leave it null. Do not guess or fabricate.",
        ),
        ("human", "Document text:\n\n{document_text}\n\nExtract all structured fields."),
    ]
)


def read_pdf_text(data: bytes) -> PdfText:
    try:
        reader = PdfReader(BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise ExtractionError(f"Could not read this PDF: {exc}") from exc

    text = "\n\n".join(pages).strip()
    if not text:
        raise ExtractionError(
            "No text found in this PDF. It is probably scanned or image-based; "
            "OCR support is not available yet."
        )
    return PdfText(text=text, page_count=len(pages))


def extract_invoice(document_text: str) -> tuple[ExtractedInvoice, bool]:
    """Returns the extracted fields and whether the text had to be truncated."""
    settings = get_settings()
    if not settings.groq_api_key:
        raise ExtractionError("GROQ_API_KEY is not configured on the server.")

    truncated = len(document_text) > settings.extraction_max_chars
    if truncated:
        document_text = document_text[: settings.extraction_max_chars]

    llm = ChatGroq(
        model=settings.extraction_model,
        temperature=0,
        api_key=settings.groq_api_key,
        max_tokens=4096,
    )
    chain = EXTRACTION_PROMPT | llm.with_structured_output(ExtractedInvoice)
    result = chain.invoke({"document_text": document_text})

    if isinstance(result, dict):
        result = ExtractedInvoice(**result)
    return result, truncated
