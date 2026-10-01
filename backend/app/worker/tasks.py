import logging
import uuid

from app.db.session import SessionLocal
from app.models import Invoice, InvoiceStatus, LineItem
from app.services.extraction import ExtractionError, extract_invoice, read_pdf_text
from app.services.storage import get_storage
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


def _fail(invoice_id: uuid.UUID, message: str) -> None:
    with SessionLocal() as db:
        invoice = db.get(Invoice, invoice_id)
        if invoice:
            invoice.status = InvoiceStatus.FAILED
            invoice.error = message[:2000]
            db.commit()


@celery_app.task(bind=True, max_retries=MAX_RETRIES)
def process_invoice(self, invoice_id: str) -> str:
    """queued -> processing -> needs_review (or failed)."""
    invoice_uuid = uuid.UUID(invoice_id)

    with SessionLocal() as db:
        invoice = db.get(Invoice, invoice_uuid)
        if invoice is None:
            logger.warning("Invoice %s no longer exists, skipping", invoice_id)
            return "missing"
        invoice.status = InvoiceStatus.PROCESSING
        invoice.error = None
        storage_key = invoice.storage_key
        db.commit()

    try:
        pdf = read_pdf_text(get_storage().get(storage_key))
        extracted, truncated = extract_invoice(pdf.text)
    except ExtractionError as exc:
        # Permanent problem with the document or configuration: do not retry.
        _fail(invoice_uuid, str(exc))
        return "failed"
    except Exception as exc:
        # Likely transient (rate limit, network): retry with exponential backoff.
        if self.request.retries >= MAX_RETRIES:
            logger.exception("Invoice %s failed after retries", invoice_id)
            _fail(invoice_uuid, f"{type(exc).__name__}: {exc}")
            return "failed"
        raise self.retry(exc=exc, countdown=10 * 2**self.request.retries) from exc

    with SessionLocal() as db:
        invoice = db.get(Invoice, invoice_uuid)
        if invoice is None:
            return "missing"

        fields = extracted.model_dump(exclude={"line_items"})
        for name, value in fields.items():
            setattr(invoice, name, value)
        invoice.line_items = [
            LineItem(position=index, **item.model_dump())
            for index, item in enumerate(extracted.line_items)
        ]
        invoice.raw_extraction = extracted.model_dump()
        invoice.page_count = pdf.page_count
        invoice.text_truncated = truncated
        invoice.status = InvoiceStatus.NEEDS_REVIEW
        db.commit()

    return "needs_review"
