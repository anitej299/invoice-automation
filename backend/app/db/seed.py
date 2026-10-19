import argparse
from datetime import timedelta
from decimal import Decimal
from sqlalchemy import select
from app.core.config import settings
from app.core.security import passwords
from app.db.session import SessionLocal
from app.models.entities import User, Invoice
from app.schemas.invoice import Extraction
from app.services.lifecycle import apply_extraction, audit, today, transition, monitor
from app.services.validation import REQUIRED


def seed(demo=False):
    cfg = settings()
    with SessionLocal() as db:
        if not db.scalar(
            select(User).where(User.email == cfg.seed_admin_email.lower())
        ):
            if len(cfg.seed_admin_password) < 12:
                raise ValueError("Set SEED_ADMIN_PASSWORD to at least 12 characters")
            db.add(
                User(
                    email=cfg.seed_admin_email.lower(),
                    password_hash=passwords.hash(cfg.seed_admin_password),
                )
            )
            db.commit()
        if not demo or db.scalar(select(Invoice.id).limit(1)):
            return
        names = [
            "Northstar Design",
            "Orbit Cloud",
            "Papertrail Office",
            "Atlas Logistics",
            "Northstar Design",
            "Cedar Consulting",
            "Meridian Systems",
            "Copper Studio",
            "Nimbus Hosting",
            "Harbor Analytics",
        ]
        cases = [
            "Valid",
            "Paid",
            "Overdue",
            "Due soon",
            "Duplicate",
            "Missing PO",
            "High value",
            "Invalid total",
            "Invalid dates",
            "Low confidence",
        ]
        for n, (vendor, case) in enumerate(zip(names, cases)):
            data = Extraction(
                invoice_number=f"DEMO-{1 if n == 4 else n + 1:03}",
                vendor_name=vendor,
                vendor_email=f"accounts{n}@example.test",
                vendor_address="12 Example Avenue, Bengaluru",
                customer_name="Acme Finance",
                customer_address="42 Sample Road, Bengaluru",
                invoice_date=today() - timedelta(days=30),
                due_date=today() + timedelta(days=14),
                purchase_order_number=f"PO-{n + 100}",
                currency="INR",
                subtotal=Decimal("10000"),
                tax=Decimal("1800"),
                discount=Decimal(0),
                total=Decimal("11800"),
                payment_terms="Net 30",
                confidence={k: 0.98 for k in REQUIRED},
                line_items=[
                    {
                        "description": "Professional services",
                        "quantity": 1,
                        "unit_price": 10000,
                        "tax": 1800,
                        "amount": 11800,
                    }
                ],
            )
            if n == 2:
                data.due_date = today() - timedelta(days=9)
            if n == 3:
                data.due_date = today() + timedelta(days=4)
            if n == 5:
                data.purchase_order_number = None
            if n == 6:
                data.subtotal, data.tax, data.total = (
                    Decimal("600000"),
                    Decimal("108000"),
                    Decimal("708000"),
                )
                (
                    data.line_items[0].unit_price,
                    data.line_items[0].tax,
                    data.line_items[0].amount,
                ) = data.subtotal, data.tax, data.total
            if n == 7:
                data.total = Decimal("15000")
            if n == 8:
                data.due_date = today() - timedelta(days=40)
            if n == 9:
                data.confidence = {k: 0.3 for k in REQUIRED}
                data.warnings = ["Blurred source document"]
            invoice = Invoice(source_filename=f"demo-{n + 1:02}.pdf")
            db.add(invoice)
            db.flush()
            audit(
                db,
                invoice,
                "invoice_received",
                f"Fictional seed scenario: {case}",
                "seed",
            )
            apply_extraction(db, invoice, data, "seed")
            if n in {1, 2, 3}:
                transition(db, invoice, "APPROVED", "seed", "Sample approval")
            if n == 1:
                transition(
                    db,
                    invoice,
                    "PAID",
                    "seed",
                    "Fictional payment reference DEMO-PAY-2",
                )
            db.commit()
        monitor(db)
        db.commit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true")
    seed(parser.parse_args().demo)
