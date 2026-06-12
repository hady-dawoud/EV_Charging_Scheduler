"""Grid advisory clients for disabled, recorded, and local HTTP modes."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol, Sequence
from urllib import error, request

from .contracts import (
    BatchGridAdvisoryRequest,
    BatchGridAdvisoryResponse,
    GridAdvisoryResponse,
    GridScheduleProposal,
    neutral_grid_advisory_response,
)
from .replay_store import ReplayGridAdvisoryStore


class GridAdvisoryClient(Protocol):
    """Minimal client protocol used by training and runtime policy code."""

    def evaluate(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        """Evaluate one station proposal."""

    def batch_evaluate(self, proposals: Sequence[GridScheduleProposal]) -> list[GridAdvisoryResponse]:
        """Evaluate proposals in request order."""


class DisabledGridAdvisoryClient:
    """Neutral client used when grid signals are intentionally disabled."""

    mode = "disabled"

    def evaluate(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        del proposal
        return neutral_grid_advisory_response()

    def batch_evaluate(self, proposals: Sequence[GridScheduleProposal]) -> list[GridAdvisoryResponse]:
        return [self.evaluate(proposal) for proposal in proposals]


class RecordedGridAdvisoryClient:
    """Replay-backed advisory client for offline training."""

    mode = "recorded"

    def __init__(
        self,
        replay_dir: str | Path,
        *,
        min_truth_level: str = "any",
        exclude_adapter_proxy: bool = False,
    ) -> None:
        self.store = ReplayGridAdvisoryStore(
            replay_dir,
            min_truth_level=min_truth_level,
            exclude_adapter_proxy=exclude_adapter_proxy,
        )

    def evaluate(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        return self.store.lookup(proposal)

    def batch_evaluate(self, proposals: Sequence[GridScheduleProposal]) -> list[GridAdvisoryResponse]:
        return [self.evaluate(proposal) for proposal in proposals]


class HttpGridAdvisoryClient:
    """HTTP client for the local DigitalTwin advisory FastAPI service."""

    mode = "http"

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8091",
        timeout_seconds: float = 2.0,
        fail_closed: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = max(float(timeout_seconds), 0.1)
        self.fail_closed = bool(fail_closed)

    def evaluate(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        responses = self.batch_evaluate([proposal])
        return responses[0] if responses else self._fallback_response(["grid_http_empty_response"])

    def batch_evaluate(self, proposals: Sequence[GridScheduleProposal]) -> list[GridAdvisoryResponse]:
        if not proposals:
            return []
        payload = BatchGridAdvisoryRequest(proposals=list(proposals)).model_dump(mode="json")
        try:
            response_payload = self._post_json("/v1/proposals/batch-evaluate", payload)
            response = BatchGridAdvisoryResponse.model_validate(response_payload)
            if len(response.responses) == len(proposals):
                return list(response.responses)
            return [self._fallback_response(["grid_http_response_count_mismatch"]) for _ in proposals]
        except Exception as exc:
            if self.fail_closed:
                raise RuntimeError("Grid advisory HTTP request failed.") from exc
            return [self._fallback_response(["grid_http_unavailable"]) for _ in proposals]

    def _post_json(self, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            f"{self.base_url}{path}",
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Grid advisory HTTP {exc.code}: {detail}") from exc

    @staticmethod
    def _fallback_response(reason_codes: list[str]) -> GridAdvisoryResponse:
        return neutral_grid_advisory_response(
            model_version="http_grid_advisory_unavailable",
            reason_codes=reason_codes,
            advisory_available=False,
        )


class RuntimeHttpGridAdvisoryClient(HttpGridAdvisoryClient):
    """HTTP client for the final 48-step runtime advisory service."""

    mode = "runtime_http"

    def __init__(
        self,
        *,
        base_url: str = "http://127.0.0.1:8088",
        timeout_seconds: float = 2.0,
        fail_closed: bool = False,
        snapshot_id: str = "demo-snapshot-48",
        client_id: str = "ev-side-runtime",
    ) -> None:
        super().__init__(base_url=base_url, timeout_seconds=timeout_seconds, fail_closed=fail_closed)
        self.snapshot_id = snapshot_id
        self.client_id = client_id

    def evaluate(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        try:
            payload = self._runtime_payload(proposal)
            response_payload = self._post_json("/v1/proposals/evaluate", payload)
            return self._runtime_response_to_ev_contract(proposal, response_payload)
        except Exception as exc:
            if self.fail_closed:
                raise RuntimeError("Runtime grid advisory HTTP request failed.") from exc
            return neutral_grid_advisory_response(
                model_version="runtime_grid_advisory_unavailable",
                reason_codes=["runtime_grid_http_unavailable"],
                advisory_available=False,
            )

    def batch_evaluate(self, proposals: Sequence[GridScheduleProposal]) -> list[GridAdvisoryResponse]:
        return [self.evaluate(proposal) for proposal in proposals]

    def _runtime_payload(self, proposal: GridScheduleProposal) -> dict:
        schedule_kw = [0.0 for _ in range(48)]
        if proposal.ev_schedule:
            for point in proposal.ev_schedule:
                if 0 <= point.time_index < 48:
                    schedule_kw[point.time_index] += float(point.p_kw)
        else:
            active_steps = max(min(int(proposal.duration_steps), 48), 1)
            step_hours = proposal.timebase_minutes / 60.0
            average_kw = proposal.requested_energy_kwh / max(active_steps * step_hours, 1e-9)
            p_kw = min(float(proposal.charger_kw), average_kw)
            for step in range(active_steps):
                schedule_kw[step] = p_kw
        return {
            "schema_version": "grid_ev_advisory.v1",
            "proposal_id": proposal.request_id,
            "client_id": self.client_id,
            "area_id": proposal.area_id,
            "snapshot_id": self.snapshot_id,
            "timebase_minutes": proposal.timebase_minutes,
            "horizon_steps": 48,
            "submitted_schedule": [
                {
                    "step": step,
                    "ev_kw": round(value, 6),
                    "station_id": proposal.station_id,
                    "node_id": proposal.node_id,
                }
                for step, value in enumerate(schedule_kw)
            ],
            "requested_energy_kwh": proposal.requested_energy_kwh,
            "metadata": {
                "episode_id": proposal.episode_id,
                "station_id": proposal.station_id,
                "secondary_area_id": proposal.secondary_area_id,
                "demand_point_id": proposal.demand_point_id,
                "source_system": proposal.source_system,
            },
        }

    def _runtime_response_to_ev_contract(self, proposal: GridScheduleProposal, payload: dict) -> GridAdvisoryResponse:
        predictions = payload["predictions"]
        counter_offer = payload["counter_offer"]
        provenance = payload["provenance"]
        gates = payload.get("gates") or {}
        v_min = min(predictions["v_min_pu"])
        max_line = max(predictions["worst_edge_loading_percent"])
        max_trafo = max(predictions["worst_trafo_loading_percent"])
        stress = max(predictions["stress_score"])
        active_steps = self._active_runtime_steps(proposal)
        caps = counter_offer["recommended_max_ev_kw_by_time"]
        active_caps = [caps[step] for step in active_steps] if active_steps else caps
        max_allowed_kw = min(active_caps) if active_caps else 0.0
        feasible_energy = float(counter_offer["served_kwh"]) + float(counter_offer["deferred_kwh"])
        binding_edge = _first_nested(predictions.get("binding_edge_ids_by_time") or [])
        binding_node = _first_nested(predictions.get("binding_node_ids_by_time") or [])
        bottleneck_type = "line" if binding_edge else "bus" if binding_node else "none"
        if "transformer_thermal_limit" in counter_offer.get("binding_constraints", []):
            bottleneck_type = "transformer"
        return GridAdvisoryResponse(
            verdict=payload["verdict"],
            risk_class=_risk_class(payload["verdict"]),
            v_min_pu=v_min,
            max_line_loading_percent=max_line,
            max_trafo_loading_percent=max_trafo,
            stress_score=stress,
            baseline_v_min_pu=1.0,
            post_v_min_pu=v_min,
            delta_v_min_pu=round(v_min - 1.0, 6),
            baseline_max_line_loading_percent=0.0,
            post_max_line_loading_percent=max_line,
            delta_max_line_loading_percent=max_line,
            baseline_max_trafo_loading_percent=0.0,
            post_max_trafo_loading_percent=max_trafo,
            delta_max_trafo_loading_percent=max_trafo,
            voltage_violation_count=sum(1 for value in predictions["v_min_pu"] if value < 0.94),
            line_overload_count=sum(1 for value in predictions["worst_edge_loading_percent"] if value > 100.0),
            trafo_overload_count=sum(1 for value in predictions["worst_trafo_loading_percent"] if value > 100.0),
            bottleneck_element_id=binding_edge or binding_node,
            bottleneck_element_type=bottleneck_type,
            bottleneck_margin_percent=round(100.0 - max(max_line, max_trafo), 6),
            max_allowed_kw=max_allowed_kw,
            curtailment_required_kw=max(float(proposal.charger_kw) - max_allowed_kw, 0.0),
            feasible_energy_kwh=feasible_energy,
            opf_feasible=payload["verdict"] != "REJECT",
            opf_curtailment_kwh=float(counter_offer["curtailed_kwh"]),
            ood_flag=(gates.get("ood") or {}).get("status") != "pass",
            uq_flag=(gates.get("uq") or {}).get("status") != "pass",
            confidence_score=_confidence(payload["verdict"], payload.get("model_status")),
            reason_codes=list(payload.get("reason_codes") or []),
            model_version=provenance["model_id"],
            evaluation_mode_used="hybrid",
            advisory_available=True,
            physical_truth_level="adapter_proxy",
            label_source_kind="adapter_proxy",
            candidate_replay_confidence=_confidence(payload["verdict"], payload.get("model_status")),
            source_snapshot_id=provenance.get("snapshot_id"),
            source_scenario_id=payload.get("audit_id"),
            source_time_index=0,
        )

    @staticmethod
    def _active_runtime_steps(proposal: GridScheduleProposal) -> list[int]:
        if proposal.ev_schedule:
            return sorted({point.time_index for point in proposal.ev_schedule if 0 <= point.time_index < 48})
        return list(range(max(min(int(proposal.duration_steps), 48), 1)))


def build_grid_advisory_client(
    *,
    mode: str = "disabled",
    replay_dir: str | Path | None = None,
    base_url: str | None = None,
    timeout_seconds: float = 2.0,
    fail_closed: bool = False,
    min_truth_level: str = "any",
    exclude_adapter_proxy: bool = False,
) -> GridAdvisoryClient:
    """Build a client from explicit mode/options."""

    normalized = str(mode or "disabled").strip().lower()
    if normalized == "recorded":
        if replay_dir is None:
            return DisabledGridAdvisoryClient()
        return RecordedGridAdvisoryClient(
            replay_dir,
            min_truth_level=min_truth_level,
            exclude_adapter_proxy=exclude_adapter_proxy,
        )
    if normalized == "http":
        return HttpGridAdvisoryClient(
            base_url=base_url or "http://127.0.0.1:8091",
            timeout_seconds=timeout_seconds,
            fail_closed=fail_closed,
        )
    if normalized == "runtime_http":
        return RuntimeHttpGridAdvisoryClient(
            base_url=base_url or "http://127.0.0.1:8088",
            timeout_seconds=timeout_seconds,
            fail_closed=fail_closed,
        )
    return DisabledGridAdvisoryClient()


def grid_advisory_client_from_env() -> GridAdvisoryClient:
    """Build a client from EV-side environment variables."""

    mode = os.getenv("GRID_ADVISORY_MODE", "disabled")
    replay_dir = os.getenv("GRID_ADVISORY_REPLAY_DIR")
    base_url = os.getenv("GRID_ADVISORY_BASE_URL")
    fail_closed = os.getenv("GRID_ADVISORY_FAIL_CLOSED", "false").strip().lower() in {"1", "true", "yes", "on"}
    timeout = float(os.getenv("GRID_ADVISORY_TIMEOUT_SECONDS", "2.0"))
    min_truth_level = os.getenv("GRID_ADVISORY_MIN_TRUTH_LEVEL", "any")
    exclude_adapter_proxy = os.getenv("GRID_ADVISORY_EXCLUDE_ADAPTER_PROXY", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return build_grid_advisory_client(
        mode=mode,
        replay_dir=replay_dir,
        base_url=base_url,
        timeout_seconds=timeout,
        fail_closed=fail_closed,
        min_truth_level=min_truth_level,
        exclude_adapter_proxy=exclude_adapter_proxy,
    )


__all__ = [
    "DisabledGridAdvisoryClient",
    "GridAdvisoryClient",
    "HttpGridAdvisoryClient",
    "RecordedGridAdvisoryClient",
    "RuntimeHttpGridAdvisoryClient",
    "build_grid_advisory_client",
    "grid_advisory_client_from_env",
]


def _risk_class(verdict: str) -> str:
    if verdict == "OK":
        return "SAFE"
    if verdict == "CAUTIOUS":
        return "NEAR"
    return "VIOLATION"


def _confidence(verdict: str, model_status: str | None) -> float:
    if verdict == "OK" and model_status == "checkpoint_accepted":
        return 0.92
    if verdict == "CAUTIOUS":
        return 0.62
    if verdict == "REJECT":
        return 0.72
    return 0.4


def _first_nested(values: list[list[str]]) -> str | None:
    for row in values:
        if row:
            return row[0]
    return None
