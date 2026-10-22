import hashlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models import Invoice, InvoiceStatus
from app.schemas.invoice import InvoiceDetail, InvoiceList, InvoiceSummary, UploadResult
from app.services.storage import Storage, get_storage

router = APIRouter(prefix="/invoices", tags=["invoices"])

PDF_MAGIC = b"%PDF-"


def enqueue_processing(invoice_id: uuid.UUID) -> None:
    # Imported lazily so the API can be imported (and tested) without a broker.
    from app.worker.tasks import process_invoice

    process_invoice.delay(str(invoice_id))


def get_enqueue():
    return enqueue_processing


def _get_or_404(db: Session, invoice_id: uuid.UUID) -> Invoice:
    invoice = db.get(Invoice, invoice_id, options=[selectinload(Invoice.line_items)])
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.post("", response_model=list[UploadResult], status_code=202)
def upload_invoices(
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    enqueue=Depends(get_enqueue),
) -> list[UploadResult]:
    """Accepts one or more PDFs. Each file gets its own result, so one bad file
    does not reject the whole batch."""
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    results: list[UploadResult] = []

    for file in files:
        filename = file.filename or "unnamed.pdf"
        data = file.file.read(max_bytes + 1)

        if len(data) > max_bytes:
            results.append(
                UploadResult(
                    filename=filename,
                    outcome="rejected",
                    detail=f"File is larger than {get_settings().max_upload_mb} MB",
                )
            )
            continue
        if not data.startswith(PDF_MAGIC):
            results.append(
                UploadResult(filename=filename, outcome="rejected", detail="Not a PDF file")
            )
            continue

        sha256 = hashlib.sha256(data).hexdigest()
        existing = db.scalar(select(Invoice).where(Invoice.file_sha256 == sha256))
        if existing:
            results.append(
                UploadResult(
                    filename=filename,
                    outcome="duplicate",
                    detail="This exact file was already uploaded",
                    invoice=InvoiceSummary.model_validate(existing),
                )
            )
            continue

        invoice = Invoice(
            id=uuid.uuid4(),
            original_filename=filename[:255],
            file_sha256=sha256,
            size_bytes=len(data),
            status=InvoiceStatus.QUEUED,
        )
        invoice.storage_key = f"invoices/{invoice.id}.pdf"
        storage.put(invoice.storage_key, data, "application/pdf")
        db.add(invoice)
        db.commit()

        enqueue(invoice.id)
        results.append(
            UploadResult(
                filename=filename,
                outcome="accepted",
                invoice=InvoiceSummary.model_validate(invoice),
            )
        )

    return results


@router.get("", response_model=InvoiceList)
def list_invoices(
    status: InvoiceStatus | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> InvoiceList:
    query = select(Invoice)
    count = select(func.count()).select_from(Invoice)
    if status:
        query = query.where(Invoice.status == status)
        count = count.where(Invoice.status == status)

    items = db.scalars(query.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)).all()
    return InvoiceList(
        items=[InvoiceSummary.model_validate(item) for item in items],
        total=db.scalar(count) or 0,
    )


@router.get("/{invoice_id}", response_model=InvoiceDetail)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)) -> Invoice:
    return _get_or_404(db, invoice_id)


@router.get("/{invoice_id}/file")
def get_invoice_file(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> Response:
    """The original PDF, for the review screen's document viewer."""
    invoice = _get_or_404(db, invoice_id)
    return Response(
        content=storage.get(invoice.storage_key),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


@router.post("/{invoice_id}/retry", response_model=InvoiceSummary, status_code=202)
def retry_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    enqueue=Depends(get_enqueue),
) -> Invoice:
    invoice = _get_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed invoices can be retried")
    invoice.status = InvoiceStatus.QUEUED
    invoice.error = None
    db.commit()
    enqueue(invoice.id)
    return invoice
