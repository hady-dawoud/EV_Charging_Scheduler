"""Local persistence for the standalone Dundee simulator runtime."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from ev_core.contracts.events import RuntimeEvent
from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import MetricsSnapshot, RecommendationResponse, StateSnapshot


@dataclass(frozen=True)
class RuntimeArtifacts:
    """Filesystem paths for runtime persistence outside ``apps/**``."""

    root: Path
    db_path: Path
    latest_state_path: Path
    latest_metrics_path: Path
    recent_recommendations_path: Path
    latest_external_requests_path: Path
    event_log_path: Path
    runtime_status_path: Path
    storage_config_path: Path

    @classmethod
    def from_repo_root(cls, repo_root: str | Path) -> "RuntimeArtifacts":
        root = Path(repo_root).resolve() / "outputs" / "runtime"
        return cls(
            root=root,
            db_path=root / "sim_runtime.db",
            latest_state_path=root / "latest_state.json",
            latest_metrics_path=root / "latest_metrics.json",
            recent_recommendations_path=root / "recent_recommendations.json",
            latest_external_requests_path=root / "latest_external_requests.json",
            event_log_path=root / "event_log.jsonl",
            runtime_status_path=root / "runtime_status.json",
            storage_config_path=root / "runtime_storage_config.json",
        )


class RuntimeStorage:
    """SQLite-plus-JSON persistence shared by the runtime and dashboard."""

    def __init__(self, repo_root: str | Path) -> None:
        self.artifacts = RuntimeArtifacts.from_repo_root(repo_root)
        self.artifacts.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self._load_db_path()
        self._ensure_schema()

    def save_state(self, snapshot: StateSnapshot) -> None:
        payload = snapshot.model_dump(mode="json")
        self._write_json(self.artifacts.latest_state_path, payload)
        with self._connect() as connection:
            connection.execute(
                "insert into state_snapshots(recorded_at, simulated_timestamp, payload_json) values (?, ?, ?)",
                (payload["simulated_timestamp"], payload["simulated_timestamp"], json.dumps(payload)),
            )

    def save_metrics(self, metrics: MetricsSnapshot) -> None:
        payload = metrics.model_dump(mode="json")
        self._write_json(self.artifacts.latest_metrics_path, payload)
        with self._connect() as connection:
            connection.execute(
                "insert into metrics_snapshots(recorded_at, simulated_timestamp, payload_json) values (?, ?, ?)",
                (payload["simulated_timestamp"], payload["simulated_timestamp"], json.dumps(payload)),
            )

    def append_events(self, events: list[RuntimeEvent]) -> None:
        if not events:
            return
        with self.artifacts.event_log_path.open("a", encoding="utf-8") as handle, self._connect() as connection:
            for event in events:
                payload = event.model_dump(mode="json")
                connection.execute(
                    """
                    insert into runtime_events(
                        event_id, occurred_at, simulated_timestamp, event_type, severity,
                        request_id, station_id, transformer_id, zone_id, message, payload_json
                    ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["event_id"],
                        payload["occurred_at"],
                        payload["simulated_timestamp"],
                        payload["event_type"],
                        payload["severity"],
                        payload.get("request_id"),
                        payload.get("station_id"),
                        payload.get("transformer_id"),
                        payload.get("zone_id"),
                        payload.get("summary") or payload.get("message", ""),
                        json.dumps(payload),
                    ),
                )
                handle.write(json.dumps(payload) + "\n")

    def save_runtime_status(self, status: dict[str, Any]) -> None:
        """Persist lightweight runtime-loop status for the dashboard and CLI."""

        self._write_json(self.artifacts.runtime_status_path, status)

    def load_runtime_status(self) -> dict[str, Any]:
        """Return the latest persisted runtime-loop status or sensible defaults."""

        if not self.artifacts.runtime_status_path.exists():
            return {
                "loop_running": False,
                "loop_interval_seconds": 0.0,
                "runtime_mode": "replay",
                "active_policy": "overload_aware",
                "recommendation_policy_name": "weighted_score",
                "demand_multiplier": 1.0,
                "warm_start_minutes": 0,
            }
        return json.loads(self.artifacts.runtime_status_path.read_text(encoding="utf-8"))

    def save_recommendation(self, response: RecommendationResponse, limit: int = 20) -> None:
        payload = response.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                "insert into recommendations(recorded_at, request_id, client_request_id, payload_json) values (?, ?, ?, ?)",
                (payload["simulated_timestamp"], payload["request_id"], payload.get("client_request_id"), json.dumps(payload)),
            )
        recent = self.get_recent_recommendations(limit=limit)
        self._write_json(self.artifacts.recent_recommendations_path, [item.model_dump(mode="json") for item in recent])

    def save_external_request(self, request: ExternalChargingRequest, status: str = "recorded", limit: int = 20) -> None:
        payload = request.model_dump(mode="json")
        with self._connect() as connection:
            connection.execute(
                "insert into external_requests(recorded_at, client_request_id, status, payload_json) values (?, ?, ?, ?)",
                (payload["request_timestamp"], payload["client_request_id"], status, json.dumps(payload)),
            )
        recent = self.get_recent_external_requests(limit=limit)
        self._write_json(self.artifacts.latest_external_requests_path, [item.model_dump(mode="json") for item in recent])

    def load_latest_state(self) -> StateSnapshot | None:
        if not self.artifacts.latest_state_path.exists():
            return None
        return StateSnapshot.model_validate(json.loads(self.artifacts.latest_state_path.read_text(encoding="utf-8")))

    def load_latest_metrics(self) -> MetricsSnapshot | None:
        if not self.artifacts.latest_metrics_path.exists():
            return None
        return MetricsSnapshot.model_validate(json.loads(self.artifacts.latest_metrics_path.read_text(encoding="utf-8")))

    def get_recent_events(self, limit: int = 100) -> list[RuntimeEvent]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload_json from runtime_events order by rowid desc limit ?",
                (limit,),
            ).fetchall()
        return [RuntimeEvent.model_validate(json.loads(row[0])) for row in rows][::-1]

    def get_recent_recommendations(self, limit: int = 20) -> list[RecommendationResponse]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload_json from recommendations order by rowid desc limit ?",
                (limit,),
            ).fetchall()
        return [RecommendationResponse.model_validate(json.loads(row[0])) for row in rows][::-1]

    def get_recent_external_requests(self, limit: int = 20) -> list[ExternalChargingRequest]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload_json from external_requests order by rowid desc limit ?",
                (limit,),
            ).fetchall()
        return [ExternalChargingRequest.model_validate(json.loads(row[0])) for row in rows][::-1]

    def get_metrics_history(self, limit: int = 288) -> list[MetricsSnapshot]:
        with self._connect() as connection:
            rows = connection.execute(
                "select payload_json from metrics_snapshots order by rowid desc limit ?",
                (limit,),
            ).fetchall()
        return [MetricsSnapshot.model_validate(json.loads(row[0])) for row in rows][::-1]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        try:
            # Some synced/workspace-mounted drives reject SQLite's default journal writes.
            # Use an in-memory journal so the runtime can still persist a local DB file.
            connection.execute("pragma journal_mode=MEMORY")
            connection.execute("pragma synchronous=NORMAL")
            return connection
        except sqlite3.Error:
            connection.close()
            raise

    def _ensure_schema(self) -> None:
        last_error: sqlite3.Error | None = None
        candidates: list[Path] = []
        for candidate in (
            self.db_path,
            self.artifacts.root / "sim_runtime_local.db",
            self.artifacts.root / "sim_runtime_store.db",
        ):
            if candidate not in candidates:
                candidates.append(candidate)

        for candidate in candidates:
            self.db_path = candidate
            try:
                self._initialize_schema()
                self._save_db_path()
                return
            except sqlite3.Error as exc:
                if self._is_corruption_error(exc):
                    if self._quarantine_db_file(candidate):
                        try:
                            self._initialize_schema()
                            self._save_db_path()
                            return
                        except sqlite3.Error as retry_exc:
                            last_error = retry_exc
                            continue
                last_error = exc
                continue

        if last_error is not None:
            raise last_error

    def _initialize_schema(self) -> None:
        connection = self._connect()
        try:
            connection.execute(
                """
                create table if not exists state_snapshots(
                    recorded_at text,
                    simulated_timestamp text,
                    payload_json text
                )
                """
            )
            connection.execute(
                """
                create table if not exists runtime_events(
                    event_id text primary key,
                    occurred_at text,
                    simulated_timestamp text,
                    event_type text,
                    severity text,
                    request_id text,
                    station_id text,
                    transformer_id text,
                    zone_id text,
                    message text,
                    payload_json text
                )
                """
            )
            connection.execute(
                """
                create table if not exists metrics_snapshots(
                    recorded_at text,
                    simulated_timestamp text,
                    payload_json text
                )
                """
            )
            connection.execute(
                """
                create table if not exists recommendations(
                    recorded_at text,
                    request_id text,
                    client_request_id text,
                    payload_json text
                )
                """
            )
            connection.execute(
                """
                create table if not exists external_requests(
                    recorded_at text,
                    client_request_id text,
                    status text,
                    payload_json text
                )
                """
            )
            connection.commit()
        finally:
            connection.close()

    def _is_corruption_error(self, error: sqlite3.Error) -> bool:
        message = str(error).lower()
        return "malformed" in message or "not a database" in message

    def _quarantine_db_file(self, path: Path) -> bool:
        if not path.exists():
            return False
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        quarantined = path.with_name(f"{path.stem}.corrupt-{timestamp}{path.suffix}")
        try:
            path.replace(quarantined)
        except PermissionError:
            return False
        return True

    def _write_json(self, path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    def _load_db_path(self) -> Path:
        if self.artifacts.storage_config_path.exists():
            payload = json.loads(self.artifacts.storage_config_path.read_text(encoding="utf-8"))
            return Path(payload.get("db_path", self.artifacts.db_path)).resolve()
        return self.artifacts.db_path

    def _save_db_path(self) -> None:
        payload = {"db_path": str(self.db_path)}
        self.artifacts.storage_config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


__all__ = ["RuntimeArtifacts", "RuntimeStorage"]
