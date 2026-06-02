"""Verify data-driven station access eligibility for the Dundee recommender."""

from __future__ import annotations

from collections import Counter
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


REPO_ROOT = Path(__file__).resolve().parents[2]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.data.repositories import DundeeSimulationRepository

_eligibility_spec = importlib.util.spec_from_file_location(
    "ev_core.recommender.eligibility",
    EV_CORE_SRC / "ev_core" / "recommender" / "eligibility.py",
)
if _eligibility_spec is None or _eligibility_spec.loader is None:
    raise RuntimeError("Could not load station eligibility module.")
_eligibility_module = importlib.util.module_from_spec(_eligibility_spec)
sys.modules[_eligibility_spec.name] = _eligibility_module
_eligibility_spec.loader.exec_module(_eligibility_module)
StationEligibilityFilter = _eligibility_module.StationEligibilityFilter


def representative_request() -> SimpleNamespace:
    return SimpleNamespace(
        source_type="external_live",
        metadata={},
    )


def main() -> int:
    repository = DundeeSimulationRepository(REPO_ROOT)
    stations = repository.load_station_table()
    request = representative_request()
    eligibility_filter = StationEligibilityFilter()

    blocked: list[tuple[str, str, str | None]] = []
    for row in stations.to_dict(orient="records"):
        station = SimpleNamespace(**row)
        result = eligibility_filter.is_eligible(station, request)
        if not result.eligible:
            blocked.append((station.station_id, station.station_name, result.reason))

    counts = Counter(
        {
            "Total stations": len(stations),
            "Public stations": int(stations["is_public"].eq(True).sum()),
            "Fleet-only stations": int(stations["is_fleet_only"].eq(True).sum()),
            "Membership stations": int(stations["requires_membership"].eq(True).sum()),
            "Needs-followup stations": int(stations["needs_followup"].eq(True).sum()),
            "Excluded stations": int(stations["exclude_from_recommendations"].eq(True).sum()),
            "Eligible normal-user stations": len(stations) - len(blocked),
        }
    )

    print("Station access verification")
    for label in (
        "Total stations",
        "Public stations",
        "Fleet-only stations",
        "Membership stations",
        "Needs-followup stations",
        "Excluded stations",
        "Eligible normal-user stations",
    ):
        print(f"{label}: {counts[label]}")
    print("Blocked stations with reasons:")
    if not blocked:
        print("- none")
    else:
        for station_id, station_name, reason in blocked:
            print(f"- {station_id} | {station_name} | {reason}")
    return 0 if not blocked else 1


if __name__ == "__main__":
    raise SystemExit(main())
