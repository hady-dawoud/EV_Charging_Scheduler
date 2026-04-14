"""Lightweight in-process event bus for the standalone simulator runtime."""

from __future__ import annotations

from collections import defaultdict
from typing import Callable

from ev_core.contracts.events import RuntimeEvent

EventHandler = Callable[[RuntimeEvent], None]


class EventBus:
    """Publish runtime events to in-process subscribers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type or for ``*``."""

        self._subscribers[event_type].append(handler)

    def publish(self, event: RuntimeEvent) -> None:
        """Dispatch a runtime event to matching subscribers."""

        for handler in self._subscribers.get(event.event_type, []):
            handler(event)
        for handler in self._subscribers.get("*", []):
            handler(event)
