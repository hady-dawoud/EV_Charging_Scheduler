"""Utilities for working with the shared 15-minute internal time base."""

from __future__ import annotations

from datetime import datetime, timedelta

TIME_STEP_MINUTES = 15
TIME_STEP = timedelta(minutes=TIME_STEP_MINUTES)


def floor_to_timebase(value: datetime, resolution_minutes: int = TIME_STEP_MINUTES) -> datetime:
    """Floor a timestamp to the start of its containing time-base interval."""

    floored_minute = value.minute - (value.minute % resolution_minutes)
    return value.replace(minute=floored_minute, second=0, microsecond=0)


def ceil_to_timebase(value: datetime, resolution_minutes: int = TIME_STEP_MINUTES) -> datetime:
    """Ceil a timestamp to the end of its containing time-base interval."""

    floored = floor_to_timebase(value, resolution_minutes=resolution_minutes)
    if floored == value.replace(second=0, microsecond=0):
        return floored
    return floored + timedelta(minutes=resolution_minutes)


def advance_timebase(value: datetime, steps: int = 1, resolution_minutes: int = TIME_STEP_MINUTES) -> datetime:
    """Advance a timestamp by an integer number of simulator time steps."""

    return value + timedelta(minutes=resolution_minutes * steps)


def minutes_between(start: datetime, end: datetime) -> int:
    """Return the whole-minute difference between two timestamps."""

    return int((end - start).total_seconds() // 60)
