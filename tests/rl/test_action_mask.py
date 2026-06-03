from __future__ import annotations

from types import SimpleNamespace

from ev_core.recommender.ranker import CandidateContext


def test_build_station_action_mask_marks_candidate_stations_as_valid() -> None:
    from ev_core.rl.action_mask import build_station_action_mask

    stations = [
        SimpleNamespace(station_id="station-a"),
        SimpleNamespace(station_id="station-b"),
        SimpleNamespace(station_id="station-c"),
    ]
    candidate_contexts = [
        CandidateContext(
            station_id="station-a",
            station_name="A",
            zone_id="zone-1",
            transformer_id="tx-1",
            distance_km=1.0,
            estimated_wait_minutes=0,
            estimated_duration_minutes=30,
            estimated_cost_gbp=10.0,
            transformer_headroom_kw=100.0,
            current_queue=0,
            utilization=0.1,
            charger_compatible=True,
        ),
        CandidateContext(
            station_id="station-c",
            station_name="C",
            zone_id="zone-1",
            transformer_id="tx-1",
            distance_km=2.0,
            estimated_wait_minutes=5,
            estimated_duration_minutes=45,
            estimated_cost_gbp=12.0,
            transformer_headroom_kw=90.0,
            current_queue=1,
            utilization=0.3,
            charger_compatible=True,
        ),
    ]

    mask = build_station_action_mask(
        request=None,
        stations=stations,
        candidate_contexts=candidate_contexts,
    )

    assert mask == [True, False, True]


def test_build_station_action_mask_returns_all_false_when_no_candidates_exist() -> None:
    from ev_core.rl.action_mask import build_station_action_mask

    stations = [SimpleNamespace(station_id="station-a"), SimpleNamespace(station_id="station-b")]

    mask = build_station_action_mask(
        request=None,
        stations=stations,
        candidate_contexts=[],
    )

    assert mask == [False, False]
