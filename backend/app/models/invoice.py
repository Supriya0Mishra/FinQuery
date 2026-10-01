import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class InvoiceStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    FAILED = "failed"


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512))
    # SHA-256 of the file bytes: uploading the same file twice never reprocesses it.
    file_sha256: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)

    status: Mapped[str] = mapped_column(String(20), default=InvoiceStatus.QUEUED, index=True)
    error: Mapped[str | None] = mapped_column(Text)

    # Extracted fields are stored exactly as they appear in the document.
    # Parsed numeric/date columns are added with the validation engine (Phase 2).
    document_type: Mapped[str | None] = mapped_column(String(50))
    vendor_name: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str | None] = mapped_column(String(255))
    invoice_number: Mapped[str | None] = mapped_column(String(100))
    issue_date: Mapped[str | None] = mapped_column(String(50))
    due_date: Mapped[str | None] = mapped_column(String(50))
    currency: Mapped[str | None] = mapped_column(String(20))
    subtotal: Mapped[str | None] = mapped_column(String(50))
    tax_amount: Mapped[str | None] = mapped_column(String(50))
    total_amount: Mapped[str | None] = mapped_column(String(50))
    payment_terms: Mapped[str | None] = mapped_column(String(100))

    # Untouched model output, kept for audits and for building the eval set.
    raw_extraction: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    text_truncated: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    line_items: Mapped[list["LineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="LineItem.position"
    )


class LineItem(Base):
    __tablename__ = "line_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    position: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[str | None] = mapped_column(String(50))
    unit_price: Mapped[str | None] = mapped_column(String(50))
    amount: Mapped[str | None] = mapped_column(String(50))

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")
