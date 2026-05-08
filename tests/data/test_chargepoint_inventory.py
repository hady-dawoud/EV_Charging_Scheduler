from __future__ import annotations

from pathlib import Path
import importlib
import sys
import types

import pytest


try:
    _np = importlib.import_module("numpy")
    if not hasattr(_np, "__version__"):
        sys.modules.pop("numpy", None)
    _pd = importlib.import_module("pandas")
    if not hasattr(_pd, "read_csv"):
        sys.modules.pop("pandas", None)
        _pd = importlib.import_module("pandas")
except ModuleNotFoundError:
    _pd = None

pytestmark = pytest.mark.skipif(
    _pd is None or not hasattr(_pd, "read_csv"),
    reason="chargepoint inventory tests require real pandas",
)

from ev_core.data.repositories import DundeeSimulationRepository


def test_load_bundle_includes_chargepoint_inventory_with_expected_columns() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    bundle = DundeeSimulationRepository(repo_root).load_bundle()

    assert len(bundle.stations) > 0
    assert len(bundle.chargepoints) > 0
    assert {"cp_id", "station_id", "connector_type_mode", "assumed_port_kw"}.issubset(bundle.chargepoints.columns)
