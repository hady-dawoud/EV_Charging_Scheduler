from __future__ import annotations

import pandas as pd
import pytest

from ev_core.topology.scenarios import (
    TopologyScenario,
    TopologyScenarioProvider,
    TransformerScenario,
)


def test_no_scenario_preserves_station_rows_and_transformer_rows() -> None:
    stations = pd.DataFrame(
        [
            {"station_id": "station_a", "transformer_id": "tx_a"},
            {"station_id": "station_b", "transformer_id": "tx_b"},
        ]
    )
    transformers = pd.DataFrame(
        [
            {"transformer_id": "tx_a", "transformer_capacity_kw_assumed": 100.0},
            {"transformer_id": "tx_b", "transformer_capacity_kw_assumed": 200.0},
        ]
    )

    provider = TopologyScenarioProvider()

    assert provider.apply_to_station_rows(stations).equals(stations)
    assert provider.transformer_rows(transformers).equals(transformers)


def test_scenario_overrides_station_mapping_and_derates_capacity() -> None:
    stations = pd.DataFrame(
        [
            {"station_id": "station_a", "transformer_id": "tx_old"},
            {"station_id": "station_b", "transformer_id": "tx_old"},
        ]
    )
    scenario = TopologyScenario(
        scenario_id="stress",
        scenario_name="Stress",
        source="test",
        transformers=(
            TransformerScenario(
                transformer_id="tx_new",
                transformer_name="New",
                zone_id="zone_a",
                capacity_kw=500.0,
                attached_station_ids=("station_a",),
                capacity_derating_factor=0.5,
            ),
            TransformerScenario(
                transformer_id="tx_old",
                transformer_name="Old",
                zone_id="zone_a",
                capacity_kw=1000.0,
            ),
        ),
        station_to_transformer={"station_a": "tx_new"},
    )

    provider = TopologyScenarioProvider(scenario)
    mapped = provider.apply_to_station_rows(stations)
    transformers = provider.transformer_rows(pd.DataFrame())

    assert mapped.set_index("station_id").loc["station_a", "transformer_id"] == "tx_new"
    assert mapped.set_index("station_id").loc["station_b", "transformer_id"] == "tx_old"
    assert transformers.set_index("transformer_id").loc["tx_new", "transformer_capacity_kw_assumed"] == 250.0


def test_unknown_station_id_raises_clear_error() -> None:
    scenario = TopologyScenario(
        scenario_id="bad",
        scenario_name="Bad",
        source="test",
        transformers=(TransformerScenario("tx_a", "A", "zone_a", 100.0),),
        station_to_transformer={"missing_station": "tx_a"},
    )

    with pytest.raises(ValueError, match="unknown station_id values: missing_station"):
        TopologyScenarioProvider(scenario).apply_to_station_rows(pd.DataFrame([{"station_id": "station_a"}]))


def test_unknown_transformer_id_raises_clear_error() -> None:
    scenario = TopologyScenario(
        scenario_id="bad",
        scenario_name="Bad",
        source="test",
        transformers=(TransformerScenario("tx_a", "A", "zone_a", 100.0),),
        station_to_transformer={"station_a": "missing_tx"},
    )

    with pytest.raises(ValueError, match="unknown transformer_id values: missing_tx"):
        TopologyScenarioProvider(scenario).apply_to_station_rows(pd.DataFrame([{"station_id": "station_a"}]))
