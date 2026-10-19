import hashlib
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.entities import Invoice, ProcessingJob, now
from app.services.extraction import ocr_provider, extract_invoice
from app.services.lifecycle import audit, apply_extraction


def attachment_key(content, filename, message_id, attachment_id):
    return hashlib.sha256(
        (message_id + "\0" + attachment_id + "\0" + filename + "\0").encode() + content
    ).hexdigest()


def process(
    db, content, filename, message_id, attachment_id, source_email, drive_url, actor
):
    filename = Path(filename.replace("\\", "/")).name[:255]
    if Path(filename).suffix.lower() not in {".pdf", ".png", ".jpg", ".jpeg"}:
        raise HTTPException(415, "Supported files: PDF, PNG, JPG, JPEG")
    key = attachment_key(content, filename, message_id, attachment_id)
    existing = db.scalar(select(Invoice).where(Invoice.idempotency_key == key))
    if existing:
        return existing
    invoice = Invoice(
        status="PROCESSING",
        source_filename=filename,
        gmail_message_id=message_id or None,
        source_email=source_email or None,
        google_drive_url=drive_url or None,
        idempotency_key=key,
    )
    db.add(invoice)
    try:
        db.flush()
        job = ProcessingJob(invoice_id=invoice.id, status="PROCESSING")
        db.add(job)
        audit(db, invoice, "invoice_received", filename, actor)
        if drive_url:
            audit(db, invoice, "uploaded_to_drive", drive_url, actor)
        db.commit()  # Durable reservation before OCR/network calls.
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Invoice).where(Invoice.idempotency_key == key))
        if existing:
            return existing
        raise
    stage = "ocr"
    try:
        audit(db, invoice, "ocr_started", filename)
        invoice.extracted_text = ocr_provider().extract(content, filename)
        audit(
            db,
            invoice,
            "ocr_completed",
            f"Extracted {len(invoice.extracted_text)} characters",
        )
        db.commit()
        stage = "ai_extraction"
        audit(db, invoice, "ai_extraction_started", "Structured extraction started")
        db.commit()
        data = extract_invoice(invoice.extracted_text)
        audit(
            db, invoice, "ai_extraction_completed", "Schema-validated output received"
        )
        stage = "validation"
        apply_extraction(db, invoice, data)
        job.status = "COMPLETED"
        job.completed_at = now()
        db.commit()
    except Exception as exc:
        db.rollback()
        invoice = db.get(Invoice, invoice.id)
        job = db.get(ProcessingJob, job.id)
        # Never persist provider response bodies, credentials or raw tracebacks.
        message = f"{stage} failed ({type(exc).__name__}); review document and provider configuration"
        invoice.status, invoice.risk_level = "UNDER_REVIEW", "HIGH"
        invoice.validation_errors = [message]
        invoice.risk_reasons = [message]
        job.status, job.error_message, job.completed_at = "FAILED", message, now()
        audit(db, invoice, stage + "_failed", message)
        db.commit()
    return invoice
