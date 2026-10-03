from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from .config import settings


def utcnow() -> datetime:
    """Naive UTC datetime (stored as such in the DB)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today_local() -> date:
    return datetime.now(ZoneInfo(settings.timezone)).date()
