from hashlib import sha256
from sqlalchemy import select
from app.core.config import settings
from app.models.entities import Invoice

REQUIRED = (
    "invoice_number",
    "vendor_name",
    "invoice_date",
    "due_date",
    "currency",
    "total",
)


def normalized(value):
    return " ".join((value or "").casefold().split())


def business_key(data):
    if not data.vendor_name or not data.invoice_number:
        return None
    return sha256(
        (normalized(data.vendor_name) + "\0" + data.invoice_number).encode()
    ).hexdigest()


def validate(data, db, exclude_id=None):
    cfg = settings()
    errors, reasons = [], []
    for field in REQUIRED:
        value = getattr(data, field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"Missing required field: {field}")
    if data.invoice_date and data.due_date and data.due_date < data.invoice_date:
        errors.append("Due date precedes invoice date")
    if data.total is not None and data.total < 0:
        errors.append("Invoice total cannot be negative")
    if all(
        getattr(data, f) is not None for f in ("subtotal", "tax", "discount", "total")
    ):
        if (
            abs(data.subtotal + data.tax - data.discount - data.total)
            > cfg.total_tolerance
        ):
            errors.append("Invoice total does not match subtotal + tax - discount")
    else:
        reasons.append("Incomplete amounts: total arithmetic could not be verified")
    key = business_key(data)
    existing = (
        db.scalar(
            select(Invoice).where(
                Invoice.business_key == key, Invoice.id != (exclude_id or -1)
            )
        )
        if key
        else None
    )
    if existing:
        errors.append("Duplicate vendor invoice number detected")
    elif data.vendor_name and data.total is not None and data.invoice_date:
        candidates = db.scalars(
            select(Invoice).where(
                Invoice.total == data.total,
                Invoice.invoice_date == data.invoice_date,
                Invoice.id != (exclude_id or -1),
            )
        ).all()
        if any(
            normalized(i.vendor_name) == normalized(data.vendor_name)
            for i in candidates
        ):
            reasons.append("Similar vendor, total and invoice date detected")
    if data.total is not None and data.total > cfg.high_value_threshold:
        reasons.append("Invoice total exceeds configured threshold")
    if not data.purchase_order_number:
        reasons.append("Missing purchase order number")
    for field in REQUIRED:
        if data.confidence.get(field, 0) < cfg.min_extraction_confidence:
            reasons.append(f"Low or missing extraction confidence: {field}")
    reasons.extend(data.warnings)
    reasons = list(dict.fromkeys(errors + reasons))
    high = (
        bool(errors)
        or (data.total is not None and data.total > cfg.high_value_threshold * 5)
        or len(reasons) >= 4
    )
    return errors, reasons, "HIGH" if high else "MEDIUM" if reasons else "LOW", existing
