"""invoices and line items

Revision ID: 0001
Revises:
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("page_count", sa.Integer()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error", sa.Text()),
        sa.Column("document_type", sa.String(50)),
        sa.Column("vendor_name", sa.String(255)),
        sa.Column("customer_name", sa.String(255)),
        sa.Column("invoice_number", sa.String(100)),
        sa.Column("issue_date", sa.String(50)),
        sa.Column("due_date", sa.String(50)),
        sa.Column("currency", sa.String(20)),
        sa.Column("subtotal", sa.String(50)),
        sa.Column("tax_amount", sa.String(50)),
        sa.Column("total_amount", sa.String(50)),
        sa.Column("payment_terms", sa.String(100)),
        sa.Column("raw_extraction", postgresql.JSONB()),
        sa.Column("text_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_invoices_file_sha256", "invoices", ["file_sha256"], unique=True)
    op.create_index("ix_invoices_status", "invoices", ["status"])

    op.create_table(
        "line_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "invoice_id",
            sa.Uuid(),
            sa.ForeignKey("invoices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("quantity", sa.String(50)),
        sa.Column("unit_price", sa.String(50)),
        sa.Column("amount", sa.String(50)),
    )
    op.create_index("ix_line_items_invoice_id", "line_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("line_items")
    op.drop_table("invoices")
