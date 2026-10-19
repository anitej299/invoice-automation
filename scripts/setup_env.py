"""Create a local .env with generated secrets; never overwrite existing configuration."""

from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env already exists; left unchanged")
values = {
    k: secrets.token_hex(32)
    for k in (
        "POSTGRES_PASSWORD",
        "JWT_SECRET",
        "AUTOMATION_API_KEY",
        "N8N_ENCRYPTION_KEY",
        "SEED_ADMIN_PASSWORD",
    )
}
lines = []
for line in (root / ".env.example").read_text().splitlines():
    key = line.partition("=")[0]
    if key in values:
        line = key + "=" + values[key]
    if key == "DATABASE_URL":
        line = (
            "DATABASE_URL=postgresql+psycopg://invoice_app:"
            + values["POSTGRES_PASSWORD"]
            + "@postgres:5432/invoices"
        )
    lines.append(line)
target.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(
    "Created .env. Read SEED_ADMIN_EMAIL and SEED_ADMIN_PASSWORD there to sign in. Configure FINANCE_EMAIL before activating workflows."
)
