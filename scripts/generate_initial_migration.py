"""Developer utility: generate the initial frozen Alembic revision from model metadata."""

import os
import secrets
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "backend"))
os.environ.setdefault("JWT_SECRET", secrets.token_hex(32))
os.environ.setdefault("AUTOMATION_API_KEY", secrets.token_hex(32))
os.environ["DATABASE_URL"] = "sqlite://"
from sqlalchemy import create_engine
from alembic.migration import MigrationContext
from alembic.autogenerate import produce_migrations, render_python_code
from app.db.session import Base
from app.models import entities  # noqa: F401 - register model metadata

path = root / "backend/alembic/versions/0001_initial.py"
if path.exists():
    raise SystemExit("Initial migration already exists; refusing to overwrite")
with create_engine("sqlite://").connect() as connection:
    context = MigrationContext.configure(connection)
    migration = produce_migrations(context, Base.metadata)
    content = (
        '"""Initial invoice automation schema, frozen at revision 0001."""\nfrom alembic import op\nimport sqlalchemy as sa\n\nrevision = "0001"\ndown_revision = None\nbranch_labels = None\ndepends_on = None\n\ndef upgrade():\n'
        + render_python_code(migration.upgrade_ops)
        + "\n\ndef downgrade():\n"
        + render_python_code(migration.downgrade_ops)
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
print("Generated initial migration")
