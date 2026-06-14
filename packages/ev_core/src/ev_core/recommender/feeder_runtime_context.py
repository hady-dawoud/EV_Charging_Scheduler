"""Offline feeder RL runtime-context adapter."""

from __future__ import annotations

import hashlib
import csv
import math
import os
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ev_core.grid_advisory.client import GridAdvisoryClient, build_grid_advisory_client
from ev_core.grid_advisory.contracts import GridAdvisoryResponse, GridSchedulePoint, GridScheduleProposal
from ev_core.rl_feeder.contracts import FeederAction, FeederRequest
from ev_core.rl_feeder.observations import FeederObservationBuilder


DEFAULT_FEEDER_RL_DATA_DIR = Path("data/processed/evside_feeder_rl")
FEEDER_POLICY_NAME = "rl_maskable_ppo_feeder"


@dataclass
class FeederRuntimeContextResult:
    runtime_context: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    context_available: bool = False


class FeederRuntimeContextError(RuntimeError):
    """Raised when strict feeder runtime-context construction fails."""


def build_feeder_runtime_context(
    request: Any,
    *,
    feeder_rl_data_dir: str | Path | None = None,
    repository: Any | None = None,
    grid_advisory_client: GridAdvisoryClient | None = None,
    grid_advisory_mode: str | None = None,
    strict: bool = False,
) -> FeederRuntimeContextResult:
    """Build the runtime context expected by ``FeederMaskablePPORuntimePolicy``."""

    data_dir = Path(feeder_rl_data_dir or os.getenv("FEEDER_RL_DATA_DIR") or DEFAULT_FEEDER_RL_DATA_DIR)
    metadata: dict[str, Any] = {
        "offline_feeder_rl_adapter": True,
        "feeder_data_dir": data_dir.as_posix(),
        "feeder_context_available": False,
    }
    try:
        repo = repository or _load_repository(data_dir)
        actions = list(repo.load_actions())
        if not actions:
            raise FeederRuntimeContextError(f"No feeder actions found in {data_dir}.")
        feature_stats = repo.load_feature_stats() if hasattr(repo, "load_feature_stats") else {}
        replay_rows = _load_replay_rows(repo, metadata)
        replay_area_ids = _replay_area_ids(replay_rows)
        selected_area, area_strategy = _select_secondary_area(request, actions, replay_area_ids)
        feeder_request = _to_feeder_request(request, selected_area, area_strategy=area_strategy)
        action_mask = [_is_action_valid_for_request(action, feeder_request) for action in actions]
        valid_actions = [action for action, valid in zip(actions, action_mask) if valid]
        connector_strategy = "compatible_request_charger" if valid_actions else "incompatible_request_charger"
        advisory_mode = grid_advisory_mode or os.getenv("GRID_ADVISORY_MODE", "recorded")
        client = grid_advisory_client or _default_grid_client(
            mode=advisory_mode,
            replay_rows=replay_rows,
            data_dir=data_dir,
        )
        grid_advisories = _build_grid_advisories(
            request=feeder_request,
            actions=valid_actions,
            client=client,
        )
        builder = FeederObservationBuilder(actions=actions, feature_stats=feature_stats)
        observation = builder.build(
            request=feeder_request,
            action_mask=action_mask,
            grid_advisories=grid_advisories,
        )
        station_ids = [action.station_id for action in actions]
        advisory_metadata = _advisory_metadata(grid_advisories.values())
        metadata.update(
            {
                "feeder_context_available": True,
                "feeder_observation_shape": list(observation.shape),
                "feeder_expected_observation_shape": builder.spec.vector_size,
                "feeder_action_count": len(actions),
                "feeder_valid_action_count": int(sum(action_mask)),
                "feeder_station_ids_count": len(station_ids),
                "feeder_selected_secondary_area_id": selected_area,
                "feeder_area_strategy": area_strategy,
                "feeder_connector_strategy": connector_strategy,
                "feeder_connector_compatible": bool(valid_actions),
                "replay_coverage_status": (
                    "covered"
                    if selected_area in replay_area_ids
                    else "unknown" if not replay_area_ids else "not_covered"
                ),
                "grid_advisory_mode": getattr(client, "mode", grid_advisory_mode or "recorded"),
                "grid_advisory_available": advisory_metadata["grid_advisory_available"],
                "grid_truth_level": advisory_metadata["grid_truth_level"],
                "grid_label_source_kind": advisory_metadata["grid_label_source_kind"],
            }
        )
        return FeederRuntimeContextResult(
            runtime_context={
                "feeder_observation": observation,
                "feeder_action_mask": [bool(value) for value in action_mask],
                "feeder_station_ids": station_ids,
                "grid_advisories": grid_advisories,
            },
            metadata=metadata,
            context_available=True,
        )
    except Exception as exc:
        message = f"feeder runtime context unavailable: {exc}"
        if strict:
            raise FeederRuntimeContextError(message) from exc
        metadata["feeder_context_error"] = message
        return FeederRuntimeContextResult(metadata=metadata, context_available=False)


def _load_repository(data_dir: Path) -> Any:
    try:
        from ev_core.rl_feeder.repository import DigitalTwinFeederRLRepository

        return DigitalTwinFeederRLRepository(data_dir)
    except ImportError:
        return _LightweightFeederRepository(data_dir)


class _LightweightFeederRepository:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)

    def load_actions(self) -> list[FeederAction]:
        rows = self._read_rows("feeder_ev_action_catalog")
        return [_row_to_action(row) for row in rows]

    def load_feature_stats(self) -> dict[str, Any]:
        path = self.data_dir / "feature_stats.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def load_grid_replay(self) -> list[dict[str, Any]]:
        return self._read_rows("feeder_grid_advisory_replay")

    def _read_rows(self, stem: str) -> list[dict[str, Any]]:
        parquet_path = self.data_dir / f"{stem}.parquet"
        csv_path = self.data_dir / f"{stem}.csv"
        if parquet_path.exists():
            try:
                import pyarrow.parquet as pq
            except ImportError as exc:
                raise ImportError(f"Reading {parquet_path} requires pandas or pyarrow.") from exc
            return [dict(row) for row in pq.read_table(parquet_path).to_pylist()]
        if csv_path.exists():
            with csv_path.open("r", encoding="utf-8", newline="") as handle:
                return [dict(row) for row in csv.DictReader(handle)]
        raise FileNotFoundError(f"Missing feeder RL artifact: {parquet_path} or {csv_path}")


def _load_replay_rows(repository: Any, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    if not hasattr(repository, "load_grid_replay"):
        metadata["grid_replay_row_count"] = 0
        return []
    try:
        replay = repository.load_grid_replay()
    except Exception as exc:
        metadata["grid_replay_error"] = str(exc)
        metadata["grid_replay_row_count"] = 0
        return []
    rows = _records(replay)
    metadata["grid_replay_row_count"] = len(rows)
    return rows


def _records(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    if isinstance(value, tuple):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    if hasattr(value, "to_dict"):
        try:
            records = value.to_dict(orient="records")
        except TypeError:
            records = value.to_dict()
        if isinstance(records, list):
            return [dict(item) for item in records if isinstance(item, Mapping)]
    return []


def _row_to_action(row: Mapping[str, Any]) -> FeederAction:
    metadata = {
        str(key): value
        for key, value in row.items()
        if key
        not in {
            "station_id",
            "secondary_area_id",
            "demand_point_id",
            "node_id",
            "p_base_kw",
            "public_ev_capacity_kw",
            "charger_kw",
            "connector_type",
            "latitude",
            "longitude",
            "x",
            "y",
            "truth_status",
            "source_system",
        }
    }
    return FeederAction(
        station_id=str(row["station_id"]),
        secondary_area_id=str(row["secondary_area_id"]),
        demand_point_id=str(row["demand_point_id"]),
        node_id=str(row["node_id"]),
        p_base_kw=_as_float(row.get("p_base_kw"), 0.0),
        public_ev_capacity_kw=max(_as_float(row.get("public_ev_capacity_kw"), 22.0), 0.0),
        charger_kw=max(_as_float(row.get("charger_kw"), 22.0), 0.0),
        connector_type=str(row.get("connector_type") or "ac").lower(),
        latitude=_optional_float(row.get("latitude")),
        longitude=_optional_float(row.get("longitude")),
        x=_optional_float(row.get("x")),
        y=_optional_float(row.get("y")),
        truth_status=str(row.get("truth_status") or "feeder_aligned"),
        source_system=str(row.get("source_system") or "digitaltwin_phase39"),
        metadata=metadata,
    )


def _replay_area_ids(rows: Iterable[Mapping[str, Any]]) -> set[str]:
    area_ids: set[str] = set()
    for row in rows:
        area = row.get("secondary_area_id") or row.get("area_id")
        if area is not None and str(area).strip():
            area_ids.add(str(area))
    return area_ids


def _select_secondary_area(
    request: Any,
    actions: Sequence[FeederAction],
    replay_area_ids: set[str],
) -> tuple[str, str]:
    action_area_ids = sorted({action.secondary_area_id for action in actions})
    if not action_area_ids:
        raise FeederRuntimeContextError("No secondary_area_id values found in feeder action catalog.")
    metadata_area = _request_metadata(request).get("secondary_area_id") or _request_metadata(request).get("feeder_secondary_area_id")
    if metadata_area is not None and str(metadata_area) in action_area_ids:
        return str(metadata_area), "request_metadata"

    nearest = _nearest_action_area(request, actions)
    if nearest is not None:
        return nearest, "nearest_action_catalog"

    covered = sorted(set(action_area_ids).intersection(replay_area_ids))
    if covered:
        return _stable_choice(covered, _request_seed_text(request)), "deterministic_replay_covered_area"
    return _stable_choice(action_area_ids, _request_seed_text(request)), "deterministic_action_catalog_area"


def _nearest_action_area(request: SimulationRequest | ExternalChargingRequest, actions: Sequence[FeederAction]) -> str | None:
    lat = _getattr(request, "current_latitude")
    lon = _getattr(request, "current_longitude")
    if lat is None or lon is None:
        return None
    best: tuple[float, str] | None = None
    for action in actions:
        if action.latitude is None or action.longitude is None:
            continue
        distance = (float(lat) - float(action.latitude)) ** 2 + (float(lon) - float(action.longitude)) ** 2
        if best is None or distance < best[0]:
            best = (distance, action.secondary_area_id)
    return None if best is None else best[1]


def _to_feeder_request(
    request: Any,
    secondary_area_id: str,
    *,
    area_strategy: str,
) -> FeederRequest:
    arrival = _getattr(request, "arrival_ts") or _getattr(request, "request_timestamp")
    latest_finish = _getattr(request, "latest_finish_ts")
    if not isinstance(arrival, datetime):
        arrival = datetime(2024, 1, 1, 12, 0)
    if not isinstance(latest_finish, datetime) or latest_finish <= arrival:
        latest_finish = arrival + timedelta(hours=2)
    requested_energy = float(_getattr(request, "requested_energy_kwh") or 20.0)
    battery_kwh = float(_getattr(request, "battery_kwh") or max(requested_energy / 0.35, 40.0))
    current_soc = _normalize_soc(_getattr(request, "current_soc"), default=0.2)
    target_soc = _normalize_soc(_getattr(request, "target_soc"), default=min(current_soc + requested_energy / max(battery_kwh, 1.0), 0.95))
    if target_soc <= current_soc:
        target_soc = min(current_soc + max(requested_energy / max(battery_kwh, 1.0), 0.05), 1.0)
    charger_type = str(_getattr(request, "charger_type_preference") or _getattr(request, "charger_type") or "any").lower()
    return FeederRequest(
        request_id=str(_getattr(request, "request_id") or _getattr(request, "client_request_id") or "runtime-request"),
        secondary_area_id=secondary_area_id,
        arrival_timestamp=arrival,
        latest_finish_timestamp=latest_finish,
        requested_energy_kwh=requested_energy,
        battery_kwh=battery_kwh,
        current_soc=current_soc,
        target_soc=target_soc,
        charger_type_preference=charger_type,
        max_ac_kw=float(_getattr(request, "vehicle_max_ac_kw") or 22.0),
        max_dc_kw=float(_getattr(request, "vehicle_max_dc_kw") or 50.0),
        origin_latitude=_getattr(request, "current_latitude"),
        origin_longitude=_getattr(request, "current_longitude"),
        source_mix_metadata={
            "preference_mode": str(_getattr(request, "preference_mode") or ""),
            "feeder_area_strategy": area_strategy,
            "mapping_note": "offline_adapter_not_utility_verified",
        },
    )


def _build_grid_advisories(
    *,
    request: FeederRequest,
    actions: Sequence[FeederAction],
    client: GridAdvisoryClient,
) -> dict[str, GridAdvisoryResponse]:
    if not actions:
        return {}
    proposals = [_proposal_for_action(request, action) for action in actions]
    responses = client.batch_evaluate(proposals)
    return {
        action.station_id: response
        for action, response in zip(actions, responses)
    }


def _default_grid_client(*, mode: str, replay_rows: list[dict[str, Any]], data_dir: Path) -> GridAdvisoryClient:
    normalized = str(mode or "recorded").strip().lower()
    if normalized == "recorded":
        return _RecordedRowsGridClient(replay_rows)
    return build_grid_advisory_client(
        mode=normalized,
        replay_dir=os.getenv("GRID_ADVISORY_REPLAY_DIR") or data_dir,
        min_truth_level=os.getenv("GRID_ADVISORY_MIN_TRUTH_LEVEL", "any"),
        exclude_adapter_proxy=_bool_env("GRID_ADVISORY_EXCLUDE_ADAPTER_PROXY", False),
    )


class _RecordedRowsGridClient:
    mode = "recorded"

    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = list(rows)

    def evaluate(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        matches = [row for row in self.rows if str(row.get("station_id")) == proposal.station_id]
        if proposal.request_id:
            exact = [row for row in matches if str(row.get("request_id")) == proposal.request_id]
            if exact:
                return _row_to_grid_response(exact[0])
        if proposal.episode_id:
            episode = [row for row in matches if str(row.get("episode_id")) == str(proposal.episode_id)]
            if episode:
                matches = episode
        if matches:
            return _row_to_grid_response(matches[int(hashlib.sha256(proposal.request_id.encode("utf-8")).hexdigest()[:8], 16) % len(matches)])
        from ev_core.grid_advisory.contracts import neutral_grid_advisory_response

        return neutral_grid_advisory_response(
            model_version="recorded_grid_advisory_no_match",
            reason_codes=["recorded_replay_no_candidate_match"],
            advisory_available=False,
        )

    def batch_evaluate(self, proposals: Sequence[GridScheduleProposal]) -> list[GridAdvisoryResponse]:
        return [self.evaluate(proposal) for proposal in proposals]


def _row_to_grid_response(row: Mapping[str, Any]) -> GridAdvisoryResponse:
    payload = {
        field: row[field]
        for field in GridAdvisoryResponse.model_fields
        if field in row and row[field] is not None and str(row[field]) != "nan"
    }
    reason_codes = payload.get("reason_codes")
    if isinstance(reason_codes, str):
        stripped = reason_codes.strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            parsed = [part.strip() for part in stripped.split(";") if part.strip()]
        payload["reason_codes"] = parsed if isinstance(parsed, list) else [str(parsed)]
    payload.setdefault("advisory_available", True)
    payload.setdefault("model_version", "recorded_grid_advisory")
    return GridAdvisoryResponse.model_validate(payload)


def _proposal_for_action(request: FeederRequest, action: FeederAction) -> GridScheduleProposal:
    charger_limit_kw = request.max_dc_kw if _prefers_dc(request) else request.max_ac_kw
    charger_kw = max(min(action.charger_kw, action.public_ev_capacity_kw, charger_limit_kw), 0.0)
    duration_hours = max(request.requested_energy_kwh / max(charger_kw, 1.0), 0.5)
    duration_steps = max(int(math.ceil(duration_hours * 60.0 / 30.0)), 1)
    schedule = [
        GridSchedulePoint(time_index=step, p_kw=charger_kw, q_kvar=0.0)
        for step in range(duration_steps)
    ]
    return GridScheduleProposal(
        request_id=request.request_id,
        episode_id=f"offline-runtime-context::{request.secondary_area_id}",
        station_id=action.station_id,
        area_id=action.secondary_area_id,
        secondary_area_id=action.secondary_area_id,
        demand_point_id=action.demand_point_id,
        node_id=action.node_id,
        asset_type="public_ev",
        source_system=action.source_system,
        start_timestamp=request.arrival_timestamp,
        timebase_minutes=30,
        duration_steps=duration_steps,
        requested_energy_kwh=request.requested_energy_kwh,
        charger_kw=charger_kw,
        ev_schedule=schedule,
        evaluation_mode="replay",
    )


def _is_action_valid_for_request(action: FeederAction, request: FeederRequest) -> bool:
    if action.secondary_area_id != request.secondary_area_id:
        return False
    if action.charger_kw <= 0.0 or action.public_ev_capacity_kw <= 0.0:
        return False
    if _prefers_dc(request):
        return action.connector_type in {"dc", "rapid", "ultra_rapid", "ultrarapid", "any"} or action.charger_kw >= 43.0
    return action.connector_type in {"ac", "dc", "rapid", "ultra_rapid", "ultrarapid", "any"}


def _advisory_metadata(advisories: Iterable[GridAdvisoryResponse]) -> dict[str, Any]:
    for advisory in advisories:
        return {
            "grid_advisory_available": bool(advisory.advisory_available),
            "grid_truth_level": advisory.physical_truth_level,
            "grid_label_source_kind": advisory.label_source_kind,
        }
    return {
        "grid_advisory_available": False,
        "grid_truth_level": None,
        "grid_label_source_kind": None,
    }


def _request_metadata(request: Any) -> Mapping[str, Any]:
    metadata = _getattr(request, "metadata")
    return metadata if isinstance(metadata, Mapping) else {}


def _request_seed_text(request: Any) -> str:
    request_id = _getattr(request, "request_id") or _getattr(request, "client_request_id") or "request"
    timestamp = _getattr(request, "arrival_ts") or _getattr(request, "request_timestamp") or ""
    return f"{request_id}|{timestamp}"


def _stable_choice(values: Sequence[str], seed_text: str) -> str:
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return values[int(digest[:12], 16) % len(values)]


def _optional_float(value: Any) -> float | None:
    result = _as_float(value, float("nan"))
    return None if result != result else result


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return default if result != result else result


def _normalize_soc(value: Any, *, default: float) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if result > 1.0:
        result = result / 100.0
    return min(max(result, 0.0), 1.0)


def _prefers_dc(request: FeederRequest) -> bool:
    return str(request.charger_type_preference).strip().lower() in {"dc", "rapid", "ultra_rapid", "ultrarapid"}


def _getattr(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = [
    "DEFAULT_FEEDER_RL_DATA_DIR",
    "FEEDER_POLICY_NAME",
    "FeederRuntimeContextError",
    "FeederRuntimeContextResult",
    "build_feeder_runtime_context",
]
