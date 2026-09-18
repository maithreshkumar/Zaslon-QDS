"""
Timezone-aware datetime utilities for Zaslon-QDS.
Replaces deprecated datetime.utcnow() with datetime.now(timezone.utc).
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Returns the current timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
