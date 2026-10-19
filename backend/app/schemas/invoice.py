from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.common import UTCDateTime


class LineItem(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax: Decimal
    amount: Decimal


class Extraction(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    invoice_number: str | None = None
    vendor_name: str | None = None
    vendor_email: str | None = None
    vendor_address: str | None = None
    customer_name: str | None = None
    customer_address: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    purchase_order_number: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    tax: Decimal | None = None
    discount: Decimal | None = None
    total: Decimal | None = None
    payment_terms: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def confidence_range(cls, value):
        if any(not 0 <= n <= 1 for n in value.values()):
            raise ValueError("Confidence must be between 0 and 1")
        return value


class InvoiceOut(Extraction):
    model_config = ConfigDict(from_attributes=True)
    id: int
    status: str
    risk_level: str
    risk_reasons: list[str]
    validation_errors: list[str]
    source_email: str | None
    gmail_message_id: str | None
    source_filename: str | None
    google_drive_url: str | None
    extracted_text: str | None
    created_at: UTCDateTime
    updated_at: UTCDateTime
    paid_at: UTCDateTime | None
    items: list[LineItem]


class InvoicePage(BaseModel):
    items: list[InvoiceOut]
    total: int
    page: int
    page_size: int


class Login(BaseModel):
    email: str
    password: str


class Decision(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class Delivery(BaseModel):
    delivery_id: str = Field(min_length=1, max_length=255)
