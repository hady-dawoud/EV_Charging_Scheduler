from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import uuid


@dataclass(frozen=True)
class MockOcppStartResult:
    provider: str
    status: str
    transaction_id: str
    connector_id: int
    connector_type: str | None
    charger_power_kw: float | None


def _infer_connector_type(charger_label: str | None) -> str | None:
    if not charger_label:
        return "mock"

    label = charger_label.lower()

    if "dc" in label or "rapid" in label:
        return "rapid"

    if "ac" in label:
        return "ac"

    return charger_label


def _infer_power_kw(charger_label: str | None) -> float | None:
    if not charger_label:
        return 22.0

    label = charger_label.lower()

    if "dc" in label or "rapid" in label:
        return 50.0

    if "ac" in label:
        return 7.4

    return 22.0


def authorize_and_start_transaction(
    *,
    user_id: str,
    reservation_id: str,
    station_id: str,
    charger_label: str | None,
) -> MockOcppStartResult:
    """
    Mock OCPP start flow.

    This does not connect to a real charger. It exists so the app can exercise
    the user-confirmed start-session flow now, while keeping the real OCPP
    integration replaceable later.
    """
    transaction_id = f"mock_tx_{uuid.uuid4().hex[:12]}"

    return MockOcppStartResult(
        provider="mock_ocpp",
        status="accepted",
        transaction_id=transaction_id,
        connector_id=1,
        connector_type=_infer_connector_type(charger_label),
        charger_power_kw=_infer_power_kw(charger_label),
    )
