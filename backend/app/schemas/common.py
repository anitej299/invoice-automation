from datetime import datetime, timezone
from typing import Annotated
from pydantic import AfterValidator


def as_utc(value: datetime) -> datetime:
    # SQLite drops timezone metadata; persisted timestamps are always UTC.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


UTCDateTime = Annotated[datetime, AfterValidator(as_utc)]
