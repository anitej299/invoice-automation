"""Generate fictional PDF/JSON fixtures; requires reportlab (development only)."""

from datetime import date, timedelta
from pathlib import Path
import json
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

root = Path(__file__).resolve().parents[1] / "sample_data"
root.mkdir(exist_ok=True)
today = date.today()
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
    "Valid invoice",
    "Paid invoice",
    "Overdue invoice",
    "Due-soon invoice",
    "Duplicate invoice",
    "Missing PO",
    "High-value invoice",
    "Invalid total",
    "Invalid due date",
    "Low-confidence review",
]
fixtures = []
for index, (vendor, case) in enumerate(zip(names, cases)):
    n = index + 1
    record = dict(
        invoice_number=f"DEMO-{1 if n == 5 else n:03}",
        vendor_name=vendor,
        vendor_email=f"accounts{index}@example.test",
        vendor_address="12 Example Avenue, Bengaluru",
        customer_name="Acme Finance",
        customer_address="42 Sample Road, Bengaluru",
        invoice_date=str(today - timedelta(days=30)),
        due_date=str(today + timedelta(days=14)),
        purchase_order_number=f"PO-{index + 100}",
        currency="INR",
        subtotal="10000.00",
        tax="1800.00",
        discount="0.00",
        total="11800.00",
        payment_terms="Net 30",
    )
    if n == 3:
        record["due_date"] = str(today - timedelta(days=9))
    if n == 4:
        record["due_date"] = str(today + timedelta(days=4))
    if n == 6:
        record["purchase_order_number"] = None
    if n == 7:
        record.update(subtotal="600000.00", tax="108000.00", total="708000.00")
    if n == 8:
        record["total"] = "15000.00"
    if n == 9:
        record["due_date"] = str(today - timedelta(days=40))
    record["line_items"] = [
        {
            "description": "Professional services",
            "quantity": "1",
            "unit_price": record["subtotal"],
            "tax": record["tax"],
            "amount": str(float(record["subtotal"]) + float(record["tax"])),
        }
    ]
    record["confidence"] = {
        key: 0.3 if n == 10 else 0.98
        for key in (
            "invoice_number",
            "vendor_name",
            "invoice_date",
            "due_date",
            "currency",
            "total",
        )
    }
    record["warnings"] = ["Blurred source document"] if n == 10 else []
    fixtures.append(
        {"scenario": case, "filename": f"demo-{n:02}.pdf", "extraction": record}
    )
    pdf = canvas.Canvas(str(root / f"demo-{n:02}.pdf"), pagesize=(595, 842))
    pdf.setTitle(f"Fictional invoice - {case}")
    pdf.setFillColor(HexColor("#173c35"))
    pdf.rect(0, 735, 595, 107, fill=1, stroke=0)
    pdf.setFillColor(HexColor("#ffffff"))
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(42, 791, "INVOICE")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(42, 766, vendor)
    pdf.setFillColor(HexColor("#7a8c80"))
    pdf.setFont("Helvetica", 9)
    pdf.drawString(42, 704, f"FICTIONAL TEST DOCUMENT  /  {case.upper()}")
    y = 670
    for key, value in record.items():
        if key in {"line_items", "confidence", "warnings"}:
            continue
        pdf.setFont("Helvetica", 10)
        pdf.setFillColor(HexColor("#334c41"))
        pdf.drawString(42, y, f"{key}: {value or ''}")
        y -= 24
    pdf.setStrokeColor(HexColor("#d8e3db"))
    pdf.line(42, y + 6, 553, y + 6)
    y -= 20
    item = record["line_items"][0]
    pdf.setFont("Helvetica", 9)
    pdf.drawString(
        42,
        y,
        "item: "
        + " | ".join(
            str(item[k])
            for k in ("description", "quantity", "unit_price", "tax", "amount")
        ),
    )
    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(HexColor("#7a8c80"))
    pdf.drawString(
        42,
        72,
        "For software demonstration only. No payment is due. All entities are fictional.",
    )
    pdf.drawRightString(553, 72, "1 / 1")
    pdf.save()
(root / "invoices.json").write_text(
    json.dumps(fixtures, indent=2) + "\n", encoding="utf-8"
)
print("Created 10 fictional PDFs and extraction fixtures")
