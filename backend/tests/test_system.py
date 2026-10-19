from datetime import timedelta
from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import settings
from app.models.entities import Invoice, AuditLog, ProcessingJob, Reminder
from app.schemas.invoice import Extraction
from app.services.validation import validate
from app.services.extraction import extract_invoice, strict_schema
from app.services.lifecycle import transition, today
from app.services.processing import attachment_key


def test_local_parsing_preserves_exact_values():
    data = extract_invoice(
        "invoice_number: 0001-A\nvendor_name: Acme\ncurrency: Rs.\ntotal: 120.50\nitem: Design | 2 | 50 | 20.50 | 120.50"
    )
    assert data.invoice_number == "0001-A"
    assert data.currency == "Rs."
    assert data.total == Decimal("120.50")
    assert len(data.line_items) == 1
    assert data.due_date is None


@pytest.mark.parametrize(
    "field",
    ["invoice_number", "vendor_name", "invoice_date", "due_date", "currency", "total"],
)
def test_required_fields(db, valid, field):
    valid[field] = None
    assert f"Missing required field: {field}" in validate(Extraction(**valid), db)[0]


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"due_date": "2026-09-01"}, "Due date precedes invoice date"),
        ({"total": "200"}, "Invoice total does not match subtotal + tax - discount"),
    ],
)
def test_invalid_values(db, valid, changes, expected):
    assert expected in validate(Extraction(**(valid | changes)), db)[0]


def test_tolerance_and_risk(db, valid):
    assert validate(Extraction(**valid), db)[2] == "LOW"
    valid["total"] = "118.01"
    assert not validate(Extraction(**valid), db)[0]
    valid["purchase_order_number"] = None
    assert validate(Extraction(**valid), db)[2] == "MEDIUM"
    valid.update(total="700000", subtotal="700000", tax="0")
    assert validate(Extraction(**valid), db)[2] == "HIGH"
    assert (
        "Invoice total exceeds configured threshold"
        in validate(Extraction(**valid), db)[1]
    )


def test_duplicate_and_similarity(client, auth, valid):
    first = client.post("/api/invoices", json=valid, headers=auth)
    assert first.status_code == 201
    duplicate = client.post("/api/invoices", json=valid, headers=auth).json()
    assert duplicate["risk_level"] == "HIGH"
    assert "Duplicate vendor invoice number detected" in duplicate["validation_errors"]
    similar = client.post(
        "/api/invoices", json=valid | {"invoice_number": "INV-002"}, headers=auth
    ).json()
    assert "Similar vendor, total and invoice date detected" in similar["risk_reasons"]


def test_authentication(client, auth):
    assert client.get("/api/invoices").status_code == 401
    assert client.get("/api/invoices", headers=auth).status_code == 200
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "finance@example.test", "password": "wrong"},
        ).status_code
        == 401
    )


def test_payment_gate_and_idempotency(client, auth, valid, db):
    id = client.post("/api/invoices", json=valid, headers=auth).json()["id"]
    assert (
        client.post(
            f"/api/invoices/{id}/pay", json={"reason": "ref-100"}, headers=auth
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/invoices/{id}/approve", json={"reason": "Verified"}, headers=auth
        ).status_code
        == 200
    )
    response = client.post(
        f"/api/invoices/{id}/pay", json={"reason": "ref-100"}, headers=auth
    )
    assert response.json()["paid_at"]
    assert response.json()["status"] == "PAID"
    client.post(f"/api/invoices/{id}/pay", json={"reason": "retry"}, headers=auth)
    assert (
        len(db.scalars(select(AuditLog).where(AuditLog.action == "invoice_paid")).all())
        == 1
    )
    assert (
        client.patch(
            f"/api/invoices/{id}", json={"total": 999}, headers=auth
        ).status_code
        == 409
    )


def test_cannot_approve_invalid_invoice(client, auth, valid):
    id = client.post("/api/invoices", json=valid | {"total": "5"}, headers=auth).json()[
        "id"
    ]
    assert (
        client.post(
            f"/api/invoices/{id}/approve", json={"reason": "Override"}, headers=auth
        ).status_code
        == 409
    )
    fixed = client.patch(f"/api/invoices/{id}", json={"total": "118"}, headers=auth)
    assert fixed.json()["status"] == "VALIDATED"
    assert len(fixed.json()["items"]) == 1


def test_failed_ocr_is_durable_and_retry_safe(client, auth, db):
    args = {
        "files": {"file": ("broken.pdf", b"not a PDF", "application/pdf")},
        "data": {"gmail_message_id": "msg-1", "attachment_id": "a1"},
        "headers": auth,
    }
    first = client.post("/api/processing/invoice", **args)
    assert first.status_code == 200
    assert first.json()["status"] == "UNDER_REVIEW"
    retry = client.post("/api/processing/invoice", **args)
    assert retry.json()["id"] == first.json()["id"]
    assert db.scalar(select(ProcessingJob)).status == "FAILED"
    assert (
        client.post(
            "/api/processing/invoice", files={"file": ("x.exe", b"bad")}, headers=auth
        ).status_code
        == 415
    )


def test_multiple_attachments_are_distinct():
    assert attachment_key(b"a", "x.pdf", "msg", "a1") != attachment_key(
        b"b", "x.pdf", "msg", "a2"
    )


def test_processing_success_and_llm_failure(client, auth, valid, monkeypatch):
    class FakeOCR:
        def extract(self, *_):
            return "invoice text"

    monkeypatch.setattr("app.services.processing.ocr_provider", lambda: FakeOCR())
    monkeypatch.setattr(
        "app.services.processing.extract_invoice", lambda _: Extraction(**valid)
    )
    result = client.post(
        "/api/processing/invoice", files={"file": ("good.pdf", b"test")}, headers=auth
    )
    assert result.json()["status"] == "VALIDATED"

    def fail(_):
        raise ValueError("malformed output")

    monkeypatch.setattr("app.services.processing.extract_invoice", fail)
    failed = client.post(
        "/api/processing/invoice",
        files={"file": ("failed.pdf", b"test2")},
        headers=auth,
    ).json()
    assert failed["status"] == "UNDER_REVIEW"
    assert "ai_extraction failed" in failed["validation_errors"][0]


def test_monitor_and_reminders(client, auth, valid, db):
    key = {"X-Automation-Key": settings().automation_api_key}
    valid.update(
        invoice_date=str(today() - timedelta(days=30)),
        due_date=str(today() - timedelta(days=1)),
    )
    id = client.post("/api/invoices", json=valid, headers=auth).json()["id"]
    client.post("/api/automation/monitor", headers=key)
    assert db.get(Invoice, id).status == "VALIDATED"  # No bypass of approval.
    client.post(
        f"/api/invoices/{id}/approve", json={"reason": "Verified"}, headers=auth
    )
    client.post("/api/automation/monitor", headers=key)
    assert db.get(Invoice, id).status == "OVERDUE"
    deliveries = client.post(
        "/api/automation/notifications/claim?kind=payment", headers=key
    ).json()
    assert len(deliveries) == 1
    assert (
        client.post(
            "/api/automation/notifications/claim?kind=payment", headers=key
        ).json()
        == []
    )
    reminder_id = deliveries[0]["id"]
    assert db.get(Reminder, reminder_id).sent_at is None
    client.post(
        f"/api/automation/notifications/{reminder_id}/sent",
        json={"delivery_id": "gmail-123"},
        headers=key,
    )
    assert db.get(Reminder, reminder_id).sent_at is not None


def test_dashboard_currency_separation(client, auth, valid):
    client.post("/api/invoices", json=valid, headers=auth)
    client.post(
        "/api/invoices",
        json=valid | {"invoice_number": "USD-1", "currency": "USD"},
        headers=auth,
    )
    stats = client.get("/api/dashboard/stats", headers=auth).json()
    assert stats["total_invoices"] == 2
    assert Decimal(str(stats["amounts_by_currency"]["INR"]["total"])) == 118
    assert Decimal(str(stats["amounts_by_currency"]["USD"]["total"])) == 118
    charts = client.get("/api/dashboard/charts?currency=USD", headers=auth).json()
    assert charts["monthly_value"][0]["value"] == 118


def test_filters_sorting_and_pagination(client, auth, valid):
    client.post("/api/invoices", json=valid, headers=auth)
    assert client.get("/api/invoices?amount_min=119", headers=auth).json()["total"] == 0
    assert client.get("/api/search?q=INV", headers=auth).json()["total"] == 1
    assert client.get("/api/invoices?sort=evil", headers=auth).status_code == 422
    assert client.get("/api/invoices/high-risk", headers=auth).status_code == 200


def test_schema_is_strict():
    schema = strict_schema()
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["properties"]["confidence"]["additionalProperties"] is False


def test_terminal_status(db):
    invoice = Invoice(status="REJECTED")
    db.add(invoice)
    db.flush()
    with pytest.raises(HTTPException):
        transition(db, invoice, "PAID", "test")


def test_real_sample_pdf_pipeline(client, auth):
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "sample_data/demo-01.pdf"
    result = client.post(
        "/api/processing/invoice",
        files={"file": (path.name, path.read_bytes(), "application/pdf")},
        headers=auth,
    )
    assert result.status_code == 200
    data = result.json()
    assert data["invoice_number"] == "DEMO-001"
    assert data["total"] == "11800.00"
    assert len(data["line_items"]) == len(data["items"]) == 1
    assert data["status"] == "UNDER_REVIEW"  # Local parser always asks for review.


def test_openai_http_contract(valid, monkeypatch):
    import httpx
    from app.services import extraction

    cfg = settings()
    monkeypatch.setattr(cfg, "extraction_provider", "openai")
    monkeypatch.setattr(cfg, "openai_api_key", "test-only-not-a-real-key")

    def respond(request):
        import json

        body = json.loads(request.content)
        assert body["response_format"]["json_schema"]["strict"] is True
        assert body["messages"][1]["content"] == "untrusted invoice text"
        return httpx.Response(
            200, json={"choices": [{"message": {"content": json.dumps(valid)}}]}
        )

    original = httpx.Client
    monkeypatch.setattr(
        extraction.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    assert (
        extraction.extract_invoice("untrusted invoice text").invoice_number == "INV-001"
    )


def test_reject_is_terminal(client, auth, valid):
    id = client.post("/api/invoices", json=valid, headers=auth).json()["id"]
    assert (
        client.post(
            f"/api/invoices/{id}/reject",
            json={"reason": "Not authorized"},
            headers=auth,
        ).json()["status"]
        == "REJECTED"
    )
    assert (
        client.post(
            f"/api/invoices/{id}/approve", json={"reason": "Try again"}, headers=auth
        ).status_code
        == 409
    )


def test_automation_cannot_approve(client, auth, valid):
    id = client.post("/api/invoices", json=valid, headers=auth).json()["id"]
    assert (
        client.post(
            f"/api/invoices/{id}/approve",
            json={"reason": "No human"},
            headers={"X-Automation-Key": settings().automation_api_key},
        ).status_code
        == 401
    )
