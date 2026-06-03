from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT_PATH = Path(__file__).resolve().parents[2]
if str(REPO_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_PATH))
EV_CORE_SRC = REPO_ROOT_PATH / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))

REPO_ROOT = REPO_ROOT_PATH

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.topology.capacity_calibration import build_capacity_recommendations
from ev_core.topology.scenarios import TopologyScenarioProvider


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Dundee topology scenario mappings.")
    parser.add_argument(
        "scenario",
        nargs="?",
        default=None,
        help="Optional scenario ID or JSON path. Omit to inspect processed topology only.",
    )
    parser.add_argument(
        "--scenario",
        dest="scenario_option",
        default=None,
        help="Optional scenario ID or JSON path. Overrides the positional scenario argument.",
    )
    args = parser.parse_args()
    scenario_ref = args.scenario_option or args.scenario

    repository = DundeeSimulationRepository(Path(REPO_ROOT))
    bundle = repository.load_bundle()
    scenario = repository.load_topology_scenario(scenario_ref) if scenario_ref else None
    provider = TopologyScenarioProvider(scenario)
    stations = provider.apply_to_station_rows(bundle.stations)
    transformers = provider.transformer_rows(bundle.transformers, station_rows=stations)
    recommendations = {
        recommendation.transformer_id: recommendation
        for recommendation in build_capacity_recommendations(
            station_rows=stations,
            chargepoint_rows=bundle.chargepoints,
            transformer_rows=transformers,
        )
    }

    transformer_ids = set(transformers["transformer_id"].astype(str))
    station_transformer_ids = set(stations["transformer_id"].astype(str))
    missing_transformers = sorted(station_transformer_ids - transformer_ids)
    if missing_transformers:
        raise SystemExit(f"Stations reference missing transformers: {', '.join(missing_transformers)}")

    print(f"scenario_id: {scenario.scenario_id if scenario else 'processed_default'}")
    print(f"station_count: {len(stations)}")
    print(f"transformer_count: {len(transformers)}")
    print("station_to_transformer_counts:")
    for transformer_id, count in stations.groupby("transformer_id")["station_id"].count().sort_index().items():
        print(f"  {transformer_id}: {int(count)}")
    print("transformer_capacities_kw:")
    for row in transformers.sort_values("transformer_id").to_dict(orient="records"):
        print(f"  {row['transformer_id']}: {float(row['transformer_capacity_kw_assumed']):.3f}")
    print("connected_cp_kw:")
    for transformer_id in sorted(recommendations):
        recommendation = recommendations[transformer_id]
        print(
            f"  {transformer_id}: connected={recommendation.connected_cp_kw:.3f}; "
            f"max_single={recommendation.max_single_cp_kw:.3f}; cp_count={recommendation.attached_cp_count}"
        )
    warnings = {
        transformer_id: recommendation.warning_flags
        for transformer_id, recommendation in sorted(recommendations.items())
        if recommendation.warning_flags
    }
    print("capacity_warnings:")
    if warnings:
        for transformer_id, flags in warnings.items():
            print(f"  {transformer_id}: {', '.join(flags)}")
    else:
        print("  none")
    print("validation: every station maps to an existing transformer")


if __name__ == "__main__":
    main()
