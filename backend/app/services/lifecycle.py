from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models.entities import Invoice, InvoiceItem, AuditLog, Vendor, now
from app.services.validation import validate, business_key, normalized

TRANSITIONS = {
    "RECEIVED": {"PROCESSING", "UNDER_REVIEW"},
    "PROCESSING": {"VALIDATED", "UNDER_REVIEW"},
    "VALIDATED": {"APPROVED", "REJECTED", "UNDER_REVIEW"},
    "UNDER_REVIEW": {"APPROVED", "REJECTED", "VALIDATED"},
    "APPROVED": {"PAYMENT_PENDING", "DUE_SOON", "OVERDUE", "PAID", "REJECTED"},
    "PAYMENT_PENDING": {"DUE_SOON", "OVERDUE", "PAID", "REJECTED"},
    "DUE_SOON": {"PAYMENT_PENDING", "OVERDUE", "PAID", "REJECTED"},
    "OVERDUE": {"PAYMENT_PENDING", "DUE_SOON", "PAID", "REJECTED"},
    "PAID": set(),
    "REJECTED": set(),
}
PAYABLE = {"APPROVED", "PAYMENT_PENDING", "DUE_SOON", "OVERDUE"}


def today():
    return datetime.now(ZoneInfo(settings().timezone)).date()


def audit(db, invoice, action, description, actor="system"):
    db.add(
        AuditLog(
            invoice_id=invoice.id,
            action=action,
            description=description,
            performed_by=actor,
        )
    )


def transition(db, invoice, status, actor, reason=""):
    if status == invoice.status:
        return
    if status not in TRANSITIONS.get(invoice.status, set()):
        raise HTTPException(409, f"Cannot transition {invoice.status} to {status}")
    invoice.status = status
    if status == "PAID":
        invoice.paid_at = now()
    audit(
        db,
        invoice,
        {
            "PAID": "invoice_paid",
            "APPROVED": "invoice_approved",
            "REJECTED": "invoice_rejected",
        }.get(status, "status_changed"),
        f"{status}: {reason}",
        actor,
    )


def apply_extraction(db, invoice, data, actor="system"):
    for field, value in data.model_dump(exclude={"line_items"}).items():
        setattr(invoice, field, value)
    invoice.items = [InvoiceItem(**item.model_dump()) for item in data.line_items]
    errors, reasons, risk, duplicate = validate(data, db, invoice.id)
    invoice.validation_errors, invoice.risk_reasons, invoice.risk_level = (
        errors,
        reasons,
        risk,
    )
    invoice.business_key = None if duplicate else business_key(data)
    invoice.status = "UNDER_REVIEW" if reasons else "VALIDATED"
    if data.vendor_name:
        vendor = db.scalar(
            select(Vendor).where(Vendor.normalized_name == normalized(data.vendor_name))
        )
        if not vendor:
            db.add(
                Vendor(
                    name=data.vendor_name,
                    normalized_name=normalized(data.vendor_name),
                    email=data.vendor_email,
                    address=data.vendor_address,
                )
            )
    audit(
        db,
        invoice,
        "validation_completed",
        "; ".join(reasons) or "All validation rules passed",
        actor,
    )
    if duplicate:
        audit(
            db, invoice, "duplicate_detected", f"Matches invoice {duplicate.id}", actor
        )
    if risk == "HIGH":
        audit(db, invoice, "high_risk_detected", "; ".join(reasons), actor)
    return duplicate


def monitor(db):
    for invoice in db.scalars(
        select(Invoice).where(Invoice.status.in_(PAYABLE)).with_for_update()
    ).all():
        if invoice.due_date:
            days = (invoice.due_date - today()).days
            target = (
                "OVERDUE"
                if days < 0
                else "DUE_SOON"
                if days <= settings().due_soon_days
                else "PAYMENT_PENDING"
            )
            transition(db, invoice, target, "payment-monitor")
