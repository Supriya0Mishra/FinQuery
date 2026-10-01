"""The shape the LLM must return. Field descriptions are sent to the model as part
of the tool schema, so they double as extraction instructions."""

from pydantic import BaseModel, Field


class ExtractedLineItem(BaseModel):
    """A single line item from an invoice or receipt."""

    description: str = Field(description="Description of the item or service")
    quantity: str | None = Field(default=None, description="Quantity as it appears")
    unit_price: str | None = Field(default=None, description="Unit price as it appears")
    amount: str | None = Field(default=None, description="Line total as it appears")


class ExtractedInvoice(BaseModel):
    """Structured fields extracted from a financial document."""

    document_type: str | None = Field(default=None, description="invoice, receipt, bill, etc.")
    vendor_name: str | None = Field(default=None, description="Issuer / vendor name")
    customer_name: str | None = Field(default=None, description="Customer / recipient name")
    invoice_number: str | None = Field(default=None, description="Invoice number or document ID")
    issue_date: str | None = Field(default=None, description="Date issued in original format")
    due_date: str | None = Field(default=None, description="Payment due date if present")
    currency: str | None = Field(default=None, description="Currency symbol or code")
    subtotal: str | None = Field(default=None, description="Subtotal exactly as it appears")
    tax_amount: str | None = Field(default=None, description="Total tax exactly as it appears")
    total_amount: str | None = Field(default=None, description="Total due exactly as it appears")
    payment_terms: str | None = Field(default=None, description="e.g. Net 14, Net 30")
    line_items: list[ExtractedLineItem] = Field(default_factory=list, description="All line items")
