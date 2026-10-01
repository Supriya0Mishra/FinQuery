import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LineItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    position: int
    description: str
    quantity: str | None
    unit_price: str | None
    amount: str | None


class InvoiceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    status: str
    error: str | None
    vendor_name: str | None
    invoice_number: str | None
    issue_date: str | None
    total_amount: str | None
    created_at: datetime
    updated_at: datetime


class InvoiceDetail(InvoiceSummary):
    size_bytes: int
    page_count: int | None
    document_type: str | None
    customer_name: str | None
    due_date: str | None
    currency: str | None
    subtotal: str | None
    tax_amount: str | None
    payment_terms: str | None
    text_truncated: bool
    line_items: list[LineItemOut]


class InvoiceList(BaseModel):
    items: list[InvoiceSummary]
    total: int


class UploadResult(BaseModel):
    filename: str
    # "accepted": new invoice queued. "duplicate": same file already uploaded,
    # the existing invoice is returned. "rejected": see `detail`.
    outcome: str
    detail: str | None = None
    invoice: InvoiceSummary | None = None
