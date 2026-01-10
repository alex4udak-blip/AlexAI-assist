"""Timezone-aware datetime utilities.

This module provides helper functions for working with datetimes in a
timezone-aware manner, replacing deprecated datetime.utcnow() calls.

Python 3.12+ deprecates datetime.utcnow() in favor of timezone-aware
datetime objects using datetime.now(timezone.utc).
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime.

    This replaces the deprecated datetime.utcnow() which returns
    a naive datetime without timezone info.

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(UTC)


def utc_now_naive() -> datetime:
    """Return current UTC time as naive datetime (for DB compatibility).

    Some database configurations expect naive datetimes. This function
    returns a naive datetime that represents UTC time, similar to
    the deprecated datetime.utcnow().

    Returns:
        Naive datetime representing current UTC time
    """
    return datetime.now(UTC).replace(tzinfo=None)


def to_utc_naive(dt: datetime | None) -> datetime | None:
    """Convert a datetime to naive UTC datetime.

    Args:
        dt: Datetime to convert (can be aware or naive)

    Returns:
        Naive datetime in UTC, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure datetime is timezone-aware UTC.

    Args:
        dt: Datetime to convert

    Returns:
        Timezone-aware UTC datetime, or None if input is None
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)
