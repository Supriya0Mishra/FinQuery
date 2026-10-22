import pytest

from app.services.extraction import ExtractionError, read_pdf_text


def test_unreadable_pdf_is_a_permanent_error():
    with pytest.raises(ExtractionError, match="Could not read"):
        read_pdf_text(b"%PDF-1.4\nnot really a pdf")
