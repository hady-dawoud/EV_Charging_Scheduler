"""Runtime event contracts for the standalone simulator service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuntimeEvent(BaseModel):
    """Serializable runtime event emitted by the simulator environment and service."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: str
    occurred_at: datetime
    simulated_timestamp: datetime
    severity: str = "info"
    request_id: Optional[str] = None
    station_id: Optional[str] = None
    transformer_id: Optional[str] = None
    zone_id: Optional[str] = None
    source_type: Optional[str] = None
    summary: str = ""
    message: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_summary(self) -> "RuntimeEvent":
        """Backfill the new ``summary`` field from legacy ``message`` payloads."""

        if not self.summary and self.message:
            self.summary = self.message
        if self.message is None:
            self.message = self.summary
        return self


__all__ = ["RuntimeEvent"]
