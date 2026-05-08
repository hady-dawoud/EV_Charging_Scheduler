from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

REPO_ROOT_PATH = Path(__file__).resolve().parents[1]
if str(REPO_ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT_PATH))
EV_CORE_SRC = REPO_ROOT_PATH / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))

REPO_ROOT = REPO_ROOT_PATH

from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.topology.capacity_calibration import build_capacity_recommendations


SCENARIO_DIR = Path(REPO_ROOT) / "data" / "processed" / "topology_scenarios"
BASE_SCENARIO_PATH = SCENARIO_DIR / "dundee_synthetic_v1.json"
REALISTIC_SCENARIO_PATH = SCENARIO_DIR / "dundee_synthetic_v1_realistic.json"
STRESS_SCENARIO_PATH = SCENARIO_DIR / "dundee_synthetic_v1_stress.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrate synthetic Dundee transformer capacities from CP inventory.")
    parser.add_argument("--write", action="store_true", help="Write calibrated realistic and stress scenario JSON files.")
    args = parser.parse_args()

    repository = DundeeSimulationRepository(Path(REPO_ROOT))
    bundle = repository.load_bundle()
    recommendations = build_capacity_recommendations(
        station_rows=bundle.stations,
        chargepoint_rows=bundle.chargepoints,
        transformer_rows=bundle.transformers,
    )

    _print_recommendations(recommendations)
    if args.write:
        base = json.loads(BASE_SCENARIO_PATH.read_text(encoding="utf-8"))
        recommendation_by_id = {recommendation.transformer_id: recommendation for recommendation in recommendations}
        _write_scenario(
            base=base,
            output_path=REALISTIC_SCENARIO_PATH,
            scenario_id="dundee_synthetic_v1_realistic",
            scenario_name="Dundee Synthetic V1 Realistic Capacity",
            notes=(
                "Synthetic simulator topology with transformer active-power capacities calibrated from CP inventory "
                "using simple diversity and utilisation assumptions. Not utility-verified transformer kVA ratings."
            ),
            recommendation_by_id=recommendation_by_id,
            capacity_field="recommended_realistic_capacity_kw",
        )
        _write_scenario(
            base=base,
            output_path=STRESS_SCENARIO_PATH,
            scenario_id="dundee_synthetic_v1_stress",
            scenario_name="Dundee Synthetic V1 Stress Capacity",
            notes=(
                "Synthetic simulator topology with constrained transformer active-power capacities for overload and "
                "headroom stress testing. Not utility-verified transformer kVA ratings."
            ),
            recommendation_by_id=recommendation_by_id,
            capacity_field="recommended_stress_capacity_kw",
        )
        print(f"wrote: {REALISTIC_SCENARIO_PATH}")
        print(f"wrote: {STRESS_SCENARIO_PATH}")


def _print_recommendations(recommendations) -> None:
    headers = (
        "transformer_id",
        "station_count",
        "cp_count",
        "connected_cp_kw",
        "max_single_cp_kw",
        "current_capacity_kw",
        "current_connected_load_ratio",
        "recommended_realistic_capacity_kw",
        "recommended_stress_capacity_kw",
        "warning_flags",
    )
    print("\t".join(headers))
    for rec in recommendations:
        print(
            "\t".join(
                [
                    rec.transformer_id,
                    str(rec.attached_station_count),
                    str(rec.attached_cp_count),
                    f"{rec.connected_cp_kw:.3f}",
                    f"{rec.max_single_cp_kw:.3f}",
                    f"{rec.current_capacity_kw:.3f}",
                    f"{rec.connected_load_ratio_current:.3f}",
                    f"{rec.recommended_realistic_capacity_kw:.3f}",
                    f"{rec.recommended_stress_capacity_kw:.3f}",
                    ",".join(rec.warning_flags) or "none",
                ]
            )
        )


def _write_scenario(
    *,
    base: dict,
    output_path: Path,
    scenario_id: str,
    scenario_name: str,
    notes: str,
    recommendation_by_id: dict,
    capacity_field: str,
) -> None:
    scenario = {
        **base,
        "scenario_id": scenario_id,
        "scenario_name": scenario_name,
        "source": "calibrated_from_chargepoint_inventory",
        "notes": notes,
    }
    transformers = []
    for transformer in base["transformers"]:
        recommendation = recommendation_by_id[str(transformer["transformer_id"])]
        capacity_kw = getattr(recommendation, capacity_field)
        transformer_notes = (
            f"{notes} connected_cp_kw={recommendation.connected_cp_kw:.3f}; "
            f"max_single_cp_kw={recommendation.max_single_cp_kw:.3f}; "
            f"legacy_capacity_kw={recommendation.current_capacity_kw:.3f}; "
            f"warning_flags={','.join(recommendation.warning_flags) or 'none'}."
        )
        transformers.append(
            {
                **transformer,
                "capacity_kw": capacity_kw,
                "capacity_derating_factor": 1.0,
                "notes": transformer_notes,
                "calibration": {
                    key: value
                    for key, value in asdict(recommendation).items()
                    if key
                    in {
                        "connected_cp_kw",
                        "max_single_cp_kw",
                        "attached_cp_count",
                        "attached_station_count",
                        "current_capacity_kw",
                        "recommended_realistic_capacity_kw",
                        "recommended_stress_capacity_kw",
                        "connected_load_ratio_current",
                        "warning_flags",
                    }
                },
            }
        )
    scenario["transformers"] = transformers
    output_path.write_text(json.dumps(scenario, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
