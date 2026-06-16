from __future__ import annotations

from datetime import datetime

import pandas as pd
import pytest

from ev_core.grid_advisory.contracts import GridAdvisoryResponse
from ev_core.rl_feeder.contracts import FeederEpisodeScenario
from ev_core.rl_feeder.repository import DigitalTwinFeederRLRepository
from ev_core.rl_feeder.requests import FeederRequestGenerator
from ev_core.rl_feeder.rewards import FeederStationSelectionReward


def _write_feeder_dataset(tmp_path) -> None:
    pd.DataFrame(
        [
            {
                "station_id": "dt_public_ev:area-a:dp-1",
                "secondary_area_id": "area-a",
                "demand_point_id": "dp-1",
                "node_id": "node-1",
                "p_base_kw": 0.0,
                "public_ev_capacity_kw": 22.0,
                "charger_kw": 22.0,
                "connector_type": "ac",
                "truth_status": "feeder_aligned",
                "source_system": "digitaltwin_phase39",
            },
            {
                "station_id": "dt_public_ev:area-b:dp-2",
                "secondary_area_id": "area-b",
                "demand_point_id": "dp-2",
                "node_id": "node-2",
                "p_base_kw": 0.0,
                "public_ev_capacity_kw": 50.0,
                "charger_kw": 50.0,
                "connector_type": "rapid",
                "truth_status": "feeder_aligned",
                "source_system": "digitaltwin_phase39",
            },
        ]
    ).to_csv(tmp_path / "feeder_ev_action_catalog.csv", index=False)
    pd.DataFrame(
        [
            {
                "request_prior_id": "area-a:dundee:test",
                "secondary_area_id": "area-a",
                "source_system": "dundee",
                "source": "dundee",
                "arrival_timestamp": "2024-02-01T17:00:00+00:00",
                "requested_energy_kwh": 12.0,
                "duration_steps": 2,
                "latest_finish_timestamp": "2024-02-01T19:00:00+00:00",
                "battery_kwh": 50.0,
                "current_soc": 0.2,
                "target_soc": 0.7,
                "slack_minutes": 120,
                "charger_type_preference": "ac",
                "max_ac_kw": 22.0,
                "max_dc_kw": 50.0,
                "origin_x": 1.0,
                "origin_y": 2.0,
                "source_mix_metadata": '{"dundee":"test"}',
            }
        ]
    ).to_csv(tmp_path / "feeder_request_priors.csv", index=False)


def test_feeder_repository_loads_only_digitaltwin_public_ev_actions(tmp_path) -> None:
    _write_feeder_dataset(tmp_path)

    actions = DigitalTwinFeederRLRepository(tmp_path).load_actions()

    assert {action.truth_status for action in actions} == {"feeder_aligned"}
    assert all(action.station_id.startswith("dt_public_ev:") for action in actions)
    assert all("dundee" not in action.station_id.lower() for action in actions)


def test_feeder_env_masks_cross_feeder_actions(tmp_path) -> None:
    gymnasium = pytest.importorskip("gymnasium")
    del gymnasium
    _write_feeder_dataset(tmp_path)
    from ev_core.rl_feeder.env import FeederStationSelectionEnv

    scenario = FeederEpisodeScenario(
        scenario_id="test-scenario",
        seed=1,
        split="train",
        secondary_area_id="area-a",
        start_ts=datetime(2024, 2, 1, 17, 0),
        duration_hours=1,
        request_count=1,
    )
    env = FeederStationSelectionEnv(feeder_rl_data_dir=tmp_path, scenario=scenario)
    observation, info = env.reset(seed=1)

    assert observation.shape == env.observation_space.shape
    assert float(observation[2]) <= 1.0
    assert env.action_masks() == [True, False]
    assert info["valid_action_count"] == 1


def test_feeder_reward_uses_continuous_stress_before_verdict_changes(tmp_path) -> None:
    _write_feeder_dataset(tmp_path)
    action = DigitalTwinFeederRLRepository(tmp_path).load_actions()[0]
    request = next(
        iter(
                FeederRequestGenerator(actions=[action], seed=1).generate_for_scenario(
                    FeederEpisodeScenario(
                    scenario_id="reward-scenario",
                    seed=1,
                    split="train",
                    secondary_area_id="area-a",
                    start_ts=datetime(2024, 2, 1, 17, 0),
                    duration_hours=1,
                    request_count=1,
                )
            )
        )
    )
    reward_model = FeederStationSelectionReward()
    low_stress = GridAdvisoryResponse(verdict="OK", risk_class="SAFE", stress_score=0.1, delta_v_min_pu=-0.001)
    high_stress = GridAdvisoryResponse(verdict="OK", risk_class="SAFE", stress_score=0.7, delta_v_min_pu=-0.02)

    low_reward = reward_model.compute(selected_action=action, request=request, grid_advisory=low_stress).total
    high_reward = reward_model.compute(selected_action=action, request=request, grid_advisory=high_stress).total

    assert high_reward < low_reward
