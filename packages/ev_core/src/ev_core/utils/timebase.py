"""Utilities for working with the shared 15-minute internal time base."""

from __future__ import annotations

from datetime import datetime, timedelta

TIME_STEP_MINUTES = 15
TIME_STEP = timedelta(minutes=TIME_STEP_MINUTES)


def floor_to_timebase(value: datetime, resolution_minutes: int = TIME_STEP_MINUTES) -> datetime:
    """Floor a timestamp to the start of its containing time-base interval."""

    floored_minute = value.minute - (value.minute % resolution_minutes)
    return value.replace(minute=floored_minute, second=0, microsecond=0)
