from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import threading
import time
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
    Request,
)
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
from app.core.config import settings
from app.core.security import (
    human,
    either,
    automation,
    passwords,
    DUMMY_HASH,
    issue_token,
)
from app.db.session import get_db
from app.models.entities import Invoice, Vendor, AuditLog, Reminder, User, now
from app.schemas.invoice import (
    Extraction,
    InvoiceOut,
    InvoicePage,
    Login,
    Decision,
    Delivery,
)
from app.schemas.reporting import (
    VendorPage,
    AuditPage,
    DashboardStats,
    DashboardCharts,
    ReminderOut,
)
from app.services.lifecycle import (
    audit,
    apply_extraction,
    transition,
    monitor,
    today,
)
from app.services.processing import process

router = APIRouter(prefix="/api")
login_attempts = defaultdict(list)
login_lock = threading.Lock()


def get_invoice(db, id, lock=False):
    query = select(Invoice).where(Invoice.id == id)
    invoice = db.scalar(query.with_for_update() if lock else query)
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice


@router.get("/health")
def health(db=Depends(get_db)):
    db.execute(select(1))
    return {"status": "ok"}


@router.post("/auth/login")
def login(body: Login, request: Request, db=Depends(get_db)):
    address = request.client.host if request.client else "unknown"
    with login_lock:
        cutoff = time.monotonic() - 300
        for key in list(login_attempts):
            login_attempts[key] = [t for t in login_attempts[key] if t > cutoff]
            if not login_attempts[key]:
                del login_attempts[key]
        if len(login_attempts[address]) >= 10:
            raise HTTPException(429, "Too many login attempts; retry in five minutes")
        login_attempts[address].append(time.monotonic())
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    verified = passwords.verify(
        body.password, user.password_hash if user else DUMMY_HASH
    )
    if not user or not verified:
        raise HTTPException(401, "Invalid email or password")
    return {"access_token": issue_token(user.email), "token_type": "bearer"}


def list_invoices(
    db,
    page,
    page_size,
    q=None,
    status=None,
    risk=None,
    vendor=None,
    date_from=None,
    date_to=None,
    amount_min=None,
    amount_max=None,
    sort="created_at",
    direction="desc",
):
    query = select(Invoice)
    if q:
        term = f"%{q}%"
        query = query.where(
            or_(Invoice.invoice_number.ilike(term), Invoice.vendor_name.ilike(term))
        )
    for field, value in ((Invoice.status, status), (Invoice.risk_level, risk)):
        if value:
            query = query.where(field == value)
    if vendor:
        query = query.where(Invoice.vendor_name.ilike(f"%{vendor}%"))
    for field, value, lower in (
        (Invoice.invoice_date, date_from, True),
        (Invoice.invoice_date, date_to, False),
        (Invoice.total, amount_min, True),
        (Invoice.total, amount_max, False),
    ):
        if value is not None:
            query = query.where(field >= value if lower else field <= value)
    allowed = {
        k: getattr(Invoice, k)
        for k in (
            "created_at",
            "invoice_number",
            "vendor_name",
            "invoice_date",
            "due_date",
            "total",
            "status",
            "risk_level",
        )
    }
    if sort not in allowed or direction not in {"asc", "desc"}:
        raise HTTPException(422, "Invalid sort field or direction")
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    column = allowed[sort]
    rows = db.scalars(
        query.order_by(
            column.asc() if direction == "asc" else column.desc(), Invoice.id
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {"items": rows, "total": total, "page": page, "page_size": page_size}


@router.get("/invoices", response_model=InvoicePage)
@router.get("/search", response_model=InvoicePage)
def invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status: str | None = None,
    risk: str | None = None,
    vendor: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    sort: str = "created_at",
    direction: str = "desc",
    db=Depends(get_db),
    actor=Depends(either),
):
    return list_invoices(
        db,
        page,
        page_size,
        q,
        status,
        risk,
        vendor,
        date_from,
        date_to,
        amount_min,
        amount_max,
        sort,
        direction,
    )


@router.get("/invoices/overdue", response_model=InvoicePage)
def overdue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    actor=Depends(either),
):
    return list_invoices(db, page, page_size, status="OVERDUE")


@router.get("/invoices/due-soon", response_model=InvoicePage)
def due_soon(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    actor=Depends(either),
):
    return list_invoices(db, page, page_size, status="DUE_SOON")


@router.get("/invoices/high-risk", response_model=InvoicePage)
def high_risk(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    actor=Depends(either),
):
    return list_invoices(db, page, page_size, risk="HIGH")


@router.get("/invoices/{id}", response_model=InvoiceOut)
def invoice_detail(id: int, db=Depends(get_db), actor=Depends(human)):
    return get_invoice(db, id)


@router.post("/invoices", response_model=InvoiceOut, status_code=201)
def create_invoice(body: Extraction, db=Depends(get_db), actor=Depends(human)):
    invoice = Invoice()
    db.add(invoice)
    db.flush()
    audit(db, invoice, "invoice_received", "Manual invoice entry", actor)
    apply_extraction(db, invoice, body, actor)
    db.commit()
    return invoice


@router.patch("/invoices/{id}", response_model=InvoiceOut)
def edit_invoice(id: int, body: Extraction, db=Depends(get_db), actor=Depends(human)):
    invoice = get_invoice(db, id, True)
    if invoice.status not in {"UNDER_REVIEW", "VALIDATED"}:
        raise HTTPException(409, "Only reviewable invoices can be edited")
    current = {
        k: getattr(invoice, k) for k in Extraction.model_fields if k != "line_items"
    }
    current["line_items"] = [
        {
            k: getattr(item, k)
            for k in ("description", "quantity", "unit_price", "tax", "amount")
        }
        for item in invoice.items
    ]
    current.update(body.model_dump(exclude_unset=True))
    apply_extraction(db, invoice, Extraction.model_validate(current), actor)
    audit(
        db, invoice, "invoice_updated", "Invoice fields edited and revalidated", actor
    )
    db.commit()
    return invoice


@router.post("/invoices/{id}/approve", response_model=InvoiceOut)
def approve(id: int, body: Decision, db=Depends(get_db), actor=Depends(human)):
    invoice = get_invoice(db, id, True)
    if invoice.validation_errors:
        raise HTTPException(409, "Resolve validation errors before approval")
    transition(db, invoice, "APPROVED", actor, body.reason)
    db.commit()
    return invoice


@router.post("/invoices/{id}/reject", response_model=InvoiceOut)
def reject(id: int, body: Decision, db=Depends(get_db), actor=Depends(human)):
    invoice = get_invoice(db, id, True)
    transition(db, invoice, "REJECTED", actor, body.reason)
    db.commit()
    return invoice


@router.post("/invoices/{id}/pay", response_model=InvoiceOut)
def pay(id: int, body: Decision, db=Depends(get_db), actor=Depends(either)):
    invoice = get_invoice(db, id, True)
    transition(db, invoice, "PAID", actor, body.reason)
    db.commit()
    return invoice


@router.post("/processing/invoice", response_model=InvoiceOut)
def processing(
    file: UploadFile = File(...),
    gmail_message_id: str = Form(""),
    attachment_id: str = Form(""),
    source_email: str = Form(""),
    google_drive_url: str = Form(""),
    db=Depends(get_db),
    actor=Depends(either),
):
    content = file.file.read(settings().max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings().max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Attachment exceeds upload limit")
    if google_drive_url and not google_drive_url.startswith(
        "https://drive.google.com/"
    ):
        raise HTTPException(422, "Expected an HTTPS Google Drive URL")
    return process(
        db,
        content,
        file.filename or "invoice",
        gmail_message_id,
        attachment_id,
        source_email,
        google_drive_url,
        actor,
    )


@router.get("/vendors", response_model=VendorPage)
def vendors(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    actor=Depends(human),
):
    return {
        "items": db.scalars(
            select(Vendor)
            .order_by(Vendor.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all(),
        "total": db.scalar(select(func.count(Vendor.id))),
    }


@router.get("/audit-logs", response_model=AuditPage)
def logs(
    invoice_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db=Depends(get_db),
    actor=Depends(human),
):
    query = select(AuditLog)
    if invoice_id is not None:
        query = query.where(AuditLog.invoice_id == invoice_id)
    return {
        "items": db.scalars(
            query.order_by(AuditLog.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all(),
        "total": db.scalar(select(func.count()).select_from(query.subquery())),
    }


@router.get("/dashboard/stats", response_model=DashboardStats)
def stats(db=Depends(get_db), actor=Depends(human)):
    rows = db.scalars(select(Invoice)).all()
    counts = defaultdict(int)
    currencies = defaultdict(lambda: {"total": Decimal(0), "outstanding": Decimal(0)})
    for i in rows:
        counts[i.status] += 1
        if i.currency and i.total is not None:
            currencies[i.currency]["total"] += i.total
            if i.status not in {"PAID", "REJECTED"}:
                currencies[i.currency]["outstanding"] += i.total
    return {
        "total_invoices": len(rows),
        "pending": sum(i.status not in {"PAID", "REJECTED"} for i in rows),
        "due_soon": counts["DUE_SOON"],
        "overdue": counts["OVERDUE"],
        "paid": counts["PAID"],
        "high_risk": sum(i.risk_level == "HIGH" for i in rows),
        "amounts_by_currency": currencies,
    }


@router.get("/dashboard/charts", response_model=DashboardCharts)
def charts(currency: str = "INR", db=Depends(get_db), actor=Depends(human)):
    rows = db.scalars(select(Invoice)).all()
    status, risk, monthly, vendor, processing = (defaultdict(float) for _ in range(5))
    for i in rows:
        status[i.status] += 1
        risk[i.risk_level] += 1
        processing[str(i.created_at.date())] += 1
        if i.currency == currency:
            monthly[str(i.invoice_date or i.created_at.date())[:7]] += float(
                i.total or 0
            )
            vendor[i.vendor_name or "Unknown"] += float(i.total or 0)
    trend = []
    for days in range(29, -1, -1):
        day = today() - timedelta(days=days)
        # Historical reconstruction: excludes rejected invoices; uses paid_at rather than current PAID state.
        amount = sum(
            float(i.total or 0)
            for i in rows
            if i.currency == currency
            and i.status != "REJECTED"
            and i.due_date
            and i.due_date < day
            and i.created_at.date() <= day
            and (not i.paid_at or i.paid_at.date() > day)
        )
        trend.append({"name": str(day), "value": amount})
    series = lambda d: [{"name": k, "value": v} for k, v in sorted(d.items())]
    return {
        "by_status": series(status),
        "by_risk": series(risk),
        "monthly_value": series(monthly),
        "vendor_spending": sorted(series(vendor), key=lambda x: -x["value"])[:10],
        "processing_trend": series(processing),
        "overdue_trend": trend,
        "currency": currency,
    }


@router.post("/automation/monitor")
def payment_monitor(db=Depends(get_db), actor=Depends(automation)):
    monitor(db)
    db.commit()
    return {"status": "completed", "date": today()}


@router.post("/automation/notifications/claim")
def claim(
    kind: str = Query(pattern="^(payment|risk)$"),
    db=Depends(get_db),
    actor=Depends(automation),
):
    query = (
        select(Invoice).where(Invoice.status.in_({"DUE_SOON", "OVERDUE"}))
        if kind == "payment"
        else select(Invoice).where(
            Invoice.risk_level == "HIGH", Invoice.status == "UNDER_REVIEW"
        )
    )
    deliveries = []
    for i in db.scalars(query.with_for_update()).all():
        reminder_type = i.status if kind == "payment" else "HIGH_RISK"
        existing = db.scalar(
            select(Reminder).where(
                Reminder.invoice_id == i.id,
                Reminder.reminder_type == reminder_type,
                Reminder.reminder_date == today(),
            )
        )
        if existing:
            continue
        reminder = Reminder(
            invoice_id=i.id,
            reminder_type=reminder_type,
            reminder_date=today(),
            recipient=settings().finance_email,
        )
        try:
            with db.begin_nested():
                db.add(reminder)
                db.flush()
        except IntegrityError:
            continue
        title = {
            "DUE_SOON": "Payment Due Soon",
            "OVERDUE": "Overdue Invoice",
            "HIGH_RISK": "High-Risk Invoice Requires Review",
        }[reminder_type]
        message = f"Vendor: {i.vendor_name}\nInvoice: {i.invoice_number}\nAmount: {i.currency} {i.total}\nDue date: {i.due_date}\nDays overdue: {max(0, (today() - i.due_date).days) if i.due_date else 'Unknown'}\nDocument: {i.google_drive_url or 'Not available'}\nRisk reasons: {'; '.join(i.risk_reasons)}\nValidation failures: {'; '.join(i.validation_errors)}"
        deliveries.append(
            {
                "id": reminder.id,
                "invoice_id": i.id,
                "recipient": reminder.recipient,
                "subject": f"{title} - {i.invoice_number}",
                "message": message,
            }
        )
    db.commit()
    return deliveries


@router.post("/automation/notifications/{id}/sent")
def sent(id: int, body: Delivery, db=Depends(get_db), actor=Depends(automation)):
    reminder = db.scalar(select(Reminder).where(Reminder.id == id).with_for_update())
    if not reminder:
        raise HTTPException(404, "Reminder not found")
    if reminder.status != "SENT":
        reminder.status, reminder.sent_at, reminder.delivery_id = (
            "SENT",
            now(),
            body.delivery_id,
        )
        audit(
            db,
            db.get(Invoice, reminder.invoice_id),
            "reminder_sent",
            f"{reminder.reminder_type} to {reminder.recipient}; Gmail ID {body.delivery_id}",
            actor,
        )
    db.commit()
    return {"status": "SENT"}


@router.get("/invoices/{id}/reminders", response_model=list[ReminderOut])
def reminder_history(id: int, db=Depends(get_db), actor=Depends(human)):
    get_invoice(db, id)
    return db.scalars(
        select(Reminder).where(Reminder.invoice_id == id).order_by(Reminder.id.desc())
    ).all()
