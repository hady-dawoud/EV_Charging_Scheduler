"""Analyze RL demand realism using the current Dundee simulator inputs."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.analysis.rl_demand_realism import build_demand_realism_summary
from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.vehicles.profiles import get_default_vehicle_profiles


def main() -> int:
    repository = DundeeSimulationRepository(REPO_ROOT)
    bundle = repository.load_bundle()
    summary = build_demand_realism_summary(
        bundle=bundle,
        vehicle_profiles=get_default_vehicle_profiles(),
    )

    print("RL demand realism analysis")
    print(f"station_count: {summary['station_count']}")
    print(f"chargepoint_count: {summary['chargepoint_count']}")
    print(f"connector_count: {summary['connector_count']}")
    print(f"total_port_capacity_kw: {summary['total_port_capacity_kw']}")
    print(f"zone_count: {summary['zone_count']}")
    print(f"transformer_count: {summary['transformer_count']}")
    print(f"vehicle_profile_count: {summary['vehicle_profile_count']}")
    print("historical_request_rate_summary:")
    for year, rate_summary in summary["historical_request_rate_summary"].items():
        print(
            f"  {year}: total={rate_summary['requests_total']}, "
            f"avg_per_day={rate_summary['avg_requests_per_day']}, "
            f"avg_per_hour={rate_summary['avg_requests_per_hour']}"
        )
    print(f"average synthetic-live requested_energy_kwh: {summary['average_synthetic_live_requested_energy_kwh']}")
    print(f"average estimated duration_minutes: {summary['average_estimated_duration_minutes']}")
    print(f"estimated arrivals_per_hour: {summary['estimated_arrivals_per_hour']}")
    print(f"estimated active_cars: {summary['estimated_active_cars']}")
    print("target utilization bands:")
    for band_name, band in summary["utilization_bands"].items():
        print(
            f"  {band_name}: {int(band['min_utilization'] * 100)}%-{int(band['max_utilization'] * 100)}% "
            f"of CPs -> active_cars={band['min_active_cars']}-{band['max_active_cars']}"
        )
    print("recommended request counts by horizon:")
    for horizon_hours, band_ranges in summary["scenario_request_ranges"].items():
        print(f"  {horizon_hours}h:")
        for band_name in ("normal", "busy", "stress"):
            band = band_ranges[band_name]
            print(f"    {band_name}: {band['min_requests']}-{band['max_requests']} requests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
