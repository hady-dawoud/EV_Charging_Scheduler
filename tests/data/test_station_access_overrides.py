from __future__ import annotations

from pathlib import Path
import importlib
import sys
from uuid import uuid4

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
    reason="station access repository tests require real pandas",
)


def write_csv(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def write_minimal_station_inputs(repo_root: Path) -> None:
    processed = repo_root / "data" / "processed"
    write_csv(
        processed / "station_master.csv",
        """
station_id,station_name,postcode_mode,cp_count_total,connector_mix_total,station_max_power_kw_proxy,first_seen_year,last_seen_year,sessions_total,energy_total_kwh,latitude,longitude,location_source,notes
public_station,Public Station,DD1,2,ac,22,2024,2024,1,10,56.46,-2.97,fixture,
fleet_station,Fleet Depot,DD2,1,rapid,50,2024,2024,1,10,56.47,-2.98,fixture,Depot candidate
member_station,Member Site,DD3,1,ac,22,2024,2024,1,10,56.48,-2.99,fixture,
        """,
    )
    write_csv(
        processed / "station_locations_verified.csv",
        """
station_id,final_latitude,final_longitude,verification_status,location_confidence_final
public_station,56.46,-2.97,accepted_current,high
fleet_station,56.47,-2.98,accepted_current,high
member_station,56.48,-2.99,accepted_current,high
        """,
    )
    write_csv(
        processed / "station_zone_map.csv",
        """
station_id,zone_id,zone_name
public_station,zone-a,Zone A
fleet_station,zone-a,Zone A
member_station,zone-b,Zone B
        """,
    )
    write_csv(
        processed / "transformer_station_map.csv",
        """
station_id,transformer_id,transformer_name,station_capacity_kw_assumed
public_station,tx-a,Transformer A,44
fleet_station,tx-a,Transformer A,50
member_station,tx-b,Transformer B,22
        """,
    )
    write_csv(
        processed / "station_capacity_assumptions.csv",
        """
station_id,station_capacity_kw_assumed
public_station,44
fleet_station,50
member_station,22
        """,
    )


def load_station_table(repo_root: Path):
    from ev_core.data.repositories import DundeeSimulationRepository

    return DundeeSimulationRepository(repo_root).load_station_table().sort_values("station_id").reset_index(drop=True)


def case_root(name: str) -> Path:
    root = Path(__file__).resolve().parents[2] / "outputs" / "test_data" / f"{name}_{uuid4().hex}"
    return root


def test_missing_override_file_defaults_stations_to_public_unrestricted() -> None:
    tmp_path = case_root("missing_override")
    write_minimal_station_inputs(tmp_path)

    stations = load_station_table(tmp_path)

    assert set(stations["station_id"]) == {"public_station", "fleet_station", "member_station"}
    assert stations["is_public"].tolist() == [True, True, True]
    assert stations["is_fleet_only"].tolist() == [False, False, False]
    assert stations["requires_membership"].tolist() == [False, False, False]
    assert stations["needs_followup"].tolist() == [False, False, False]
    assert stations["exclude_from_recommendations"].tolist() == [False, False, False]
    assert stations["access_notes"].isna().all()


def test_override_file_merges_access_columns_without_dropping_station_rows() -> None:
    tmp_path = case_root("merge_override")
    write_minimal_station_inputs(tmp_path)
    write_csv(
        tmp_path / "data" / "processed" / "station_access_overrides.csv",
        """
station_id,is_public,is_fleet_only,requires_membership,needs_followup,exclude_from_recommendations,access_notes,review_status,review_source
fleet_station,false,true,false,false,false,Fleet depot by name,assumed,station_name_keyword
member_station,yes,no,1,0,false,Membership wording,needs_manual_review,station_name_keyword
        """,
    )

    stations = load_station_table(tmp_path)
    by_id = stations.set_index("station_id")

    assert len(stations) == 3
    assert by_id.loc["public_station", "is_public"] is True
    assert by_id.loc["fleet_station", "is_public"] is False
    assert by_id.loc["fleet_station", "is_fleet_only"] is True
    assert by_id.loc["member_station", "requires_membership"] is True
    assert by_id.loc["member_station", "needs_followup"] is False
    assert by_id.loc["fleet_station", "access_notes"] == "Fleet depot by name"
    assert by_id.loc["member_station", "access_review_status"] == "needs_manual_review"
    assert by_id.loc["member_station", "access_review_source"] == "station_name_keyword"


def test_boolean_override_strings_parse_common_values() -> None:
    tmp_path = case_root("boolean_override")
    write_minimal_station_inputs(tmp_path)
    write_csv(
        tmp_path / "data" / "processed" / "station_access_overrides.csv",
        """
station_id,is_public,is_fleet_only,requires_membership,needs_followup,exclude_from_recommendations,access_notes,review_status,review_source
public_station,1,0,yes,no,false,Parsed booleans,assumed,data_note
        """,
    )

    station = load_station_table(tmp_path).set_index("station_id").loc["public_station"]

    assert station["is_public"] is True
    assert station["is_fleet_only"] is False
    assert station["requires_membership"] is True
    assert station["needs_followup"] is False
    assert station["exclude_from_recommendations"] is False


def test_unknown_station_id_in_override_file_raises_clear_error() -> None:
    tmp_path = case_root("unknown_override")
    write_minimal_station_inputs(tmp_path)
    write_csv(
        tmp_path / "data" / "processed" / "station_access_overrides.csv",
        """
station_id,is_public,is_fleet_only,requires_membership,needs_followup,exclude_from_recommendations,access_notes,review_status,review_source
missing_station,false,true,false,false,false,Unknown station,assumed,station_name_keyword
        """,
    )

    with pytest.raises(ValueError, match="unknown station_id"):
        load_station_table(tmp_path)


def test_repo_station_access_overrides_keep_current_rows_public_and_reviewable() -> None:
    from ev_core.data.repositories import DundeeSimulationRepository

    repo_root = Path(__file__).resolve().parents[2]
    stations = DundeeSimulationRepository(repo_root).load_station_table()
    override_ids = {
        "greenmarket_150kw_bus_charger",
        "dundee_house_depot_north_lindsay_street_dundee",
        "south_tay_street_car_club_public",
        "alexander_street_dundee",
        "caird_avenue",
        "camperdown_country_park",
        "clepington_road_4th_hub",
        "dundee_taybridge_rail_station_south_union_street_dundee",
        "housing_office_east_midmill_road_dundee",
    }
    flagged = stations[stations["station_id"].isin(override_ids)].set_index("station_id")

    assert len(flagged) == len(override_ids)
    assert flagged["is_public"].eq(True).all()
    assert flagged["is_fleet_only"].eq(False).all()
    assert flagged["requires_membership"].eq(False).all()
    assert flagged["exclude_from_recommendations"].eq(False).all()
    assert flagged["needs_followup"].eq(True).all()
