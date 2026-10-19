import os
import secrets

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = secrets.token_hex(32)
os.environ["AUTOMATION_API_KEY"] = secrets.token_hex(32)
os.environ["SEED_ADMIN_PASSWORD"] = secrets.token_hex(16)
os.environ["EXTRACTION_PROVIDER"] = "local"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.session import Base, get_db
from app.models.entities import User
from app.core.security import passwords
from app.core.config import settings
from app.api.routes import login_attempts


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    with sessionmaker(engine, expire_on_commit=False)() as session:
        session.add(
            User(
                email="finance@example.test",
                password_hash=passwords.hash(settings().seed_admin_password),
            )
        )
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    login_attempts.clear()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def auth(client):
    token = client.post(
        "/api/auth/login",
        json={
            "email": "finance@example.test",
            "password": settings().seed_admin_password,
        },
    ).json()["access_token"]
    return {"Authorization": "Bearer " + token}


@pytest.fixture
def valid():
    return {
        "invoice_number": "INV-001",
        "vendor_name": "Example Studio",
        "invoice_date": "2026-10-01",
        "due_date": "2026-10-31",
        "currency": "INR",
        "subtotal": "100",
        "tax": "18",
        "discount": "0",
        "total": "118",
        "purchase_order_number": "PO-1",
        "confidence": {
            k: 0.99
            for k in (
                "invoice_number",
                "vendor_name",
                "invoice_date",
                "due_date",
                "currency",
                "total",
            )
        },
        "line_items": [
            {
                "description": "Design",
                "quantity": 1,
                "unit_price": 100,
                "tax": 18,
                "amount": 118,
            }
        ],
    }
