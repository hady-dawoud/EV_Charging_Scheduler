"""Recorded grid advisory replay lookup for offline RL training."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

from .contracts import GridAdvisoryResponse, GridScheduleProposal, neutral_grid_advisory_response


class ReplayGridAdvisoryStore:
    """Lookup advisory responses from a Parquet or CSV replay export."""

    def __init__(
        self,
        replay_dir: str | Path,
        *,
        min_truth_level: str = "any",
        exclude_adapter_proxy: bool = False,
    ) -> None:
        self.replay_dir = Path(replay_dir).resolve()
        self.min_truth_level = str(min_truth_level or "any")
        self.exclude_adapter_proxy = bool(exclude_adapter_proxy)
        self._frame = None

    def lookup(self, proposal: GridScheduleProposal) -> GridAdvisoryResponse:
        frame = self._load_frame()
        if frame is None or frame.empty:
            return neutral_grid_advisory_response(
                model_version="recorded_grid_advisory_missing",
                reason_codes=["recorded_replay_not_found"],
                advisory_available=False,
            )

        matches = frame[frame["station_id"].astype(str) == proposal.station_id]
        if "request_id" in matches.columns:
            exact = matches[matches["request_id"].astype(str) == proposal.request_id]
            if not exact.empty:
                return self._row_to_response(exact.iloc[0])
        if "episode_id" in matches.columns and proposal.episode_id:
            episode = matches[matches["episode_id"].astype(str) == str(proposal.episode_id)]
            if not episode.empty:
                matches = episode
        if "start_timestamp" in matches.columns:
            timestamp = proposal.start_timestamp.isoformat()
            exact_time = matches[matches["start_timestamp"].astype(str).str.startswith(timestamp[:16])]
            if not exact_time.empty:
                return self._row_to_response(_stable_select(exact_time, proposal))
        if not matches.empty:
            return self._row_to_response(_stable_select(matches, proposal))

        return neutral_grid_advisory_response(
            model_version="recorded_grid_advisory_no_match",
            reason_codes=["recorded_replay_no_candidate_match"],
            advisory_available=False,
        )

    def _load_frame(self):
        if self._frame is not None:
            return self._frame

        try:
            import pandas as pd
        except ImportError:
            self._frame = None
            return None

        for stem in ("feeder_grid_advisory_replay", "rl_candidate_advisory"):
            parquet_path = self.replay_dir / f"{stem}.parquet"
            csv_path = self.replay_dir / f"{stem}.csv"
            if parquet_path.exists():
                self._frame = self._filter_frame(pd.read_parquet(parquet_path))
                return self._frame
            if csv_path.exists():
                self._frame = self._filter_frame(pd.read_csv(csv_path))
                return self._frame
        self._frame = None
        return None

    def _filter_frame(self, frame):
        if frame is None or frame.empty:
            return frame
        result = frame.copy()
        if self.exclude_adapter_proxy and "physical_truth_level" in result.columns:
            result = result[result["physical_truth_level"].astype(str) != "adapter_proxy"].copy()
        if self.min_truth_level and self.min_truth_level != "any" and "physical_truth_level" in result.columns:
            min_rank = _truth_rank(self.min_truth_level)
            result = result[result["physical_truth_level"].astype(str).map(_truth_rank) >= min_rank].copy()
        return result.reset_index(drop=True)

    def _row_to_response(self, row: Any) -> GridAdvisoryResponse:
        payload: dict[str, Any] = {}
        for field in GridAdvisoryResponse.model_fields:
            if field in row and row[field] == row[field]:
                payload[field] = row[field]
        if isinstance(payload.get("reason_codes"), str):
            payload["reason_codes"] = _parse_reason_codes(payload["reason_codes"])
        payload.setdefault("advisory_available", True)
        payload.setdefault("model_version", "recorded_grid_advisory")
        return GridAdvisoryResponse.model_validate(payload)


def _parse_reason_codes(value: str) -> list[str]:
    stripped = value.strip()
    if not stripped:
        return []
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return [part.strip() for part in stripped.split(";") if part.strip()]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _stable_select(frame: Any, proposal: GridScheduleProposal) -> Any:
    if len(frame) <= 1:
        return frame.iloc[0]
    seed_text = "|".join(
        [
            proposal.station_id,
            proposal.request_id,
            str(proposal.episode_id or ""),
            proposal.start_timestamp.isoformat(),
        ]
    )
    digest = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
    return frame.iloc[int(digest[:12], 16) % len(frame)]


def _truth_rank(value: object) -> int:
    return {
        "adapter_proxy": 0,
        "unknown": 0,
        "opf_proxy": 1,
        "area_pf": 2,
        "node_pf": 3,
        "exact_candidate_pf": 4,
        "any": 0,
    }.get(str(value).strip().lower(), 0)


__all__ = ["ReplayGridAdvisoryStore"]
