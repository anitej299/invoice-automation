import secrets
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from pwdlib import PasswordHash
from sqlalchemy import select
from app.core.config import settings
from app.db.session import get_db
from app.models.entities import User

passwords = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
api_key = APIKeyHeader(name="X-Automation-Key", auto_error=False)
DUMMY_HASH = passwords.hash("unused-timing-equalizer")


def issue_token(email):
    return jwt.encode(
        {
            "sub": email,
            "exp": datetime.now(timezone.utc)
            + timedelta(minutes=settings().jwt_expire_minutes),
        },
        settings().jwt_secret,
        algorithm="HS256",
    )


def human(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db=Depends(get_db),
):
    try:
        payload = jwt.decode(
            credentials.credentials if credentials else "",
            settings().jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        user = db.scalar(select(User).where(User.email == payload["sub"]))
        if user:
            return user.email
    except jwt.InvalidTokenError:
        pass
    raise HTTPException(401, "Invalid or expired session")


def automation(key: str | None = Depends(api_key)):
    if not key or not secrets.compare_digest(key, settings().automation_api_key):
        raise HTTPException(401, "Invalid automation key")
    return "n8n"


def either(
    key: str | None = Depends(api_key), credentials=Depends(bearer), db=Depends(get_db)
):
    return automation(key) if key else human(credentials, db)
