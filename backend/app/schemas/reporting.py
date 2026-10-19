from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.schemas.common import UTCDateTime


class VendorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str | None
    address: str | None
    created_at: UTCDateTime


class VendorPage(BaseModel):
    items: list[VendorOut]
    total: int


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    action: str
    description: str
    performed_by: str
    created_at: UTCDateTime


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int


class Amounts(BaseModel):
    total: Decimal
    outstanding: Decimal


class DashboardStats(BaseModel):
    total_invoices: int
    pending: int
    due_soon: int
    overdue: int
    paid: int
    high_risk: int
    amounts_by_currency: dict[str, Amounts]


class Point(BaseModel):
    name: str
    value: float


class DashboardCharts(BaseModel):
    by_status: list[Point]
    by_risk: list[Point]
    monthly_value: list[Point]
    vendor_spending: list[Point]
    processing_trend: list[Point]
    overdue_trend: list[Point]
    currency: str


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_id: int
    reminder_type: str
    reminder_date: date
    sent_at: UTCDateTime | None
    recipient: str
    status: str
    delivery_id: str | None
