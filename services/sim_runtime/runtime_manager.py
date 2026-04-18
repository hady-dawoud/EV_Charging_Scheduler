"""Runtime manager for the standalone Dundee simulator service."""

from __future__ import annotations

from services.sim_runtime.bootstrap_paths import bootstrap_repo_paths

bootstrap_repo_paths()

import threading
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

from ev_core.contracts.requests import ExternalChargingRequest
from ev_core.contracts.responses import MetricsSnapshot, RecommendationResponse, StateSnapshot
from ev_core.data.repositories import DundeeSimulationRepository
from ev_core.env.environment import DundeeEnv
from ev_core.forecasting.provider import PlaceholderForecastProvider

from .event_bus import EventBus
from .storage import RuntimeStorage


@dataclass(frozen=True)
class RuntimeConfig:
    """High-level runtime configuration used by the demo manager."""

    replay_year: int = 2024
    default_policy: str = "overload_aware"
    default_runtime_mode: str = "replay"
    default_loop_interval_seconds: float = 1.0
    default_demand_multiplier: float = 1.0


class RuntimeManager:
    """Start, tick, loop, and inspect the standalone Dundee simulator runtime."""

    def __init__(self, repo_root: str | Path | None = None, config: RuntimeConfig | None = None) -> None:
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[2]).resolve()
        self.config = config or RuntimeConfig()
        self.repository = DundeeSimulationRepository(self.repo_root)
        self.bundle = self.repository.load_bundle()
        self.forecast_provider = PlaceholderForecastProvider(
            background_load=self.bundle.background_load,
            price_table=self.bundle.price_table,
            pv_profile=self.bundle.pv_profile,
        )
        self.storage = RuntimeStorage(self.repo_root)
        self.event_bus = EventBus()
        self.event_bus.subscribe("*", lambda event: None)
        self._loop_thread: threading.Thread | None = None
        self._loop_stop = threading.Event()

    def start(
        self,
        *,
        replay_day: str = "2024-06-10",
        start_hour: int = 0,
        start_minute: int = 0,
        policy_mode: str | None = None,
        replay_year: int | None = None,
        runtime_mode: str | None = None,
        demand_multiplier: float | None = None,
        warm_start_hours: int = 0,
        preset: str | None = None,
    ) -> StateSnapshot:
        """Create a fresh Dundee runtime and optionally warm it into a busy state."""

        options = self._resolve_start_options(
            replay_day=replay_day,
            start_hour=start_hour,
            start_minute=start_minute,
            policy_mode=policy_mode,
            replay_year=replay_year,
            runtime_mode=runtime_mode,
            demand_multiplier=demand_multiplier,
            warm_start_hours=warm_start_hours,
            preset=preset,
        )
        target_start = self._build_target_start(options["replay_day"], options["start_hour"], options["start_minute"])
        warm_start_minutes = max(int(options["warm_start_hours"]) * 60, 0)
        window_start = max(
            datetime.combine(target_start.date(), time.min),
            target_start - timedelta(minutes=warm_start_minutes),
        )
        window_end = datetime.combine(target_start.date(), time(hour=23, minute=45))
        env = DundeeEnv(
            self.bundle,
            policy_mode=str(options["policy_mode"]),
            replay_year=int(options["replay_year"]),
            start_time=window_start,
            runtime_mode=str(options["runtime_mode"]),
            demand_multiplier=float(options["demand_multiplier"]),
            operational_start_time=target_start,
            warm_start_minutes=warm_start_minutes,
            replay_window_start=window_start,
            replay_window_end=window_end,
            forecast_provider=self.forecast_provider,
        )
        env.start()
        self.storage.save_runtime_status(
            self._compose_runtime_status(
                env=env,
                loop_running=False,
                loop_interval_seconds=0.0,
            )
        )
        self._persist_env(env, include_events=True)
        while env.current_time < target_start:
            env.step()
            self._persist_env(env, include_events=True)
        return self.storage.load_latest_state() or env.get_state_snapshot()

    def pause(self) -> StateSnapshot:
        """Pause the latest persisted Dundee runtime."""

        self.stop_loop()
        env = self._load_env()
        snapshot = env.pause()
        self._persist_env(env, include_events=True)
        return snapshot

    def reset(
        self,
        *,
        replay_day: str = "2024-06-10",
        start_hour: int = 0,
        start_minute: int = 0,
        policy_mode: str | None = None,
        replay_year: int | None = None,
        runtime_mode: str | None = None,
        demand_multiplier: float | None = None,
        warm_start_hours: int = 0,
        preset: str | None = None,
    ) -> StateSnapshot:
        """Reset the runtime to a fresh configured Dundee state."""

        self.stop_loop()
        return self.start(
            replay_day=replay_day,
            start_hour=start_hour,
            start_minute=start_minute,
            policy_mode=policy_mode,
            replay_year=replay_year,
            runtime_mode=runtime_mode,
            demand_multiplier=demand_multiplier,
            warm_start_hours=warm_start_hours,
            preset=preset,
        )

    def tick(self, *, steps: int = 1, action: dict[str, str] | None = None) -> StateSnapshot:
        """Advance the Dundee runtime by one or more 15-minute steps."""

        env = self._load_env()
        if not env.running:
            env.start()
            self._persist_env(env, include_events=True)
        for _ in range(max(steps, 1)):
            env.step(action=action)
            self._persist_env(env, include_events=True)
        return self.storage.load_latest_state() or env.get_state_snapshot()

    def start_loop(self, *, interval_seconds: float | None = None) -> dict[str, Any]:
        """Begin continuously ticking the runtime in a background thread."""

        interval = max(float(interval_seconds or self.config.default_loop_interval_seconds), 0.1)
        if self._loop_thread is not None and self._loop_thread.is_alive():
            status = self.storage.load_runtime_status()
            status["loop_running"] = True
            status["loop_interval_seconds"] = interval
            self.storage.save_runtime_status(status)
            snapshot = self.storage.load_latest_state()
            if snapshot is not None:
                self.storage.save_state(snapshot.model_copy(update={"loop_running": True, "loop_interval_seconds": interval}))
            return status

        status = self.storage.load_runtime_status()
        status["loop_running"] = True
        status["loop_interval_seconds"] = interval
        self.storage.save_runtime_status(status)
        snapshot = self.storage.load_latest_state()
        if snapshot is not None:
            self.storage.save_state(snapshot.model_copy(update={"loop_running": True, "loop_interval_seconds": interval}))
        self._loop_stop.clear()

        def _runner() -> None:
            try:
                while not self._loop_stop.is_set():
                    loop_status = self.storage.load_runtime_status()
                    if not bool(loop_status.get("loop_running", False)):
                        break
                    self.tick(steps=1)
                    wait_seconds = max(float(loop_status.get("loop_interval_seconds", interval)), 0.1)
                    if self._loop_stop.wait(wait_seconds):
                        break
            finally:
                final_status = self.storage.load_runtime_status()
                final_status["loop_running"] = False
                self.storage.save_runtime_status(final_status)
                snapshot = self.storage.load_latest_state()
                if snapshot is not None:
                    self.storage.save_state(
                        snapshot.model_copy(
                            update={
                                "loop_running": False,
                                "loop_interval_seconds": float(final_status.get("loop_interval_seconds", interval)),
                            }
                        )
                    )

        self._loop_thread = threading.Thread(target=_runner, name="dundee-sim-loop", daemon=True)
        self._loop_thread.start()
        return status

    def stop_loop(self) -> dict[str, Any]:
        """Stop the continuous ticking loop without clearing runtime state."""

        self._loop_stop.set()
        status = self.storage.load_runtime_status()
        status["loop_running"] = False
        self.storage.save_runtime_status(status)
        if self._loop_thread is not None and self._loop_thread.is_alive():
            self._loop_thread.join(timeout=2.0)
        snapshot = self.storage.load_latest_state()
        if snapshot is not None:
            self.storage.save_state(snapshot.model_copy(update={"loop_running": False}))
        return status

    def wait_for_loop(self) -> None:
        """Block until the current runtime loop exits."""

        if self._loop_thread is not None:
            self._loop_thread.join()

    def inject_request(self, payload: ExternalChargingRequest | dict[str, Any]) -> RecommendationResponse:
        """Inject an external-style request into the current Dundee runtime."""

        env = self._load_env()
        request = payload if isinstance(payload, ExternalChargingRequest) else ExternalChargingRequest.model_validate(payload)
        sim_request = env.inject_external_request(request)
        response = env.get_ranked_recommendations(sim_request)
        self.storage.save_external_request(request, status="injected")
        self.storage.save_recommendation(response)
        self._persist_env(env, include_events=True)
        return response

    def recommend(self, payload: ExternalChargingRequest | dict[str, Any]) -> RecommendationResponse:
        """Produce a recommendation against the current runtime state without queuing the request."""

        env = self._load_env()
        request = payload if isinstance(payload, ExternalChargingRequest) else ExternalChargingRequest.model_validate(payload)
        response = env.get_ranked_recommendations(request)
        self.storage.save_recommendation(response)
        self._persist_env(env, include_events=True)
        return response

    def get_latest_state(self) -> StateSnapshot | None:
        """Return the latest persisted Dundee runtime state snapshot."""

        return self.storage.load_latest_state()

    def get_recent_events(self, limit: int = 100):
        """Return recent runtime events from local storage."""

        return self.storage.get_recent_events(limit=limit)

    def get_latest_metrics(self) -> MetricsSnapshot | None:
        """Return the latest persisted runtime metrics snapshot."""

        return self.storage.load_latest_metrics()

    def get_recent_recommendations(self, limit: int = 20) -> list[RecommendationResponse]:
        """Return recent recommendation responses."""

        return self.storage.get_recent_recommendations(limit=limit)

    def get_runtime_status(self) -> dict[str, Any]:
        """Return the latest runtime liveness status."""

        return self.storage.load_runtime_status()

    def _load_env_or_new(self, *, policy_mode: str | None = None) -> DundeeEnv:
        snapshot = self.storage.load_latest_state()
        if snapshot is None:
            return DundeeEnv(
                self.bundle,
                policy_mode=policy_mode or self.config.default_policy,
                replay_year=self.config.replay_year,
                runtime_mode=self.config.default_runtime_mode,
                demand_multiplier=self.config.default_demand_multiplier,
                forecast_provider=self.forecast_provider,
            )
        return DundeeEnv.from_state_snapshot(self.bundle, snapshot, forecast_provider=self.forecast_provider)

    def _load_env(self) -> DundeeEnv:
        snapshot = self.storage.load_latest_state()
        if snapshot is None:
            return DundeeEnv(
                self.bundle,
                policy_mode=self.config.default_policy,
                replay_year=self.config.replay_year,
                runtime_mode=self.config.default_runtime_mode,
                demand_multiplier=self.config.default_demand_multiplier,
                forecast_provider=self.forecast_provider,
            )
        return DundeeEnv.from_state_snapshot(self.bundle, snapshot, forecast_provider=self.forecast_provider)

    def _persist_env(self, env: DundeeEnv, *, include_events: bool = False) -> StateSnapshot:
        status = self.storage.load_runtime_status()
        base_snapshot = env.get_state_snapshot()
        snapshot = base_snapshot.model_copy(
            update={
                "runtime_mode": env.runtime_mode,
                "demand_multiplier": env.demand_multiplier,
                "warm_start_minutes": env.warm_start_minutes,
                "loop_running": bool(status.get("loop_running", False)),
                "loop_interval_seconds": float(status.get("loop_interval_seconds", 0.0)),
                "operational_start_ts": env.operational_start_time,
                "metadata": {
                    **base_snapshot.metadata,
                    "runtime_status_updated_at": datetime.utcnow().isoformat(),
                },
            }
        )
        self.storage.save_state(snapshot)
        self.storage.save_metrics(snapshot.metrics)
        self.storage.save_runtime_status(
            self._compose_runtime_status(
                env=env,
                loop_running=snapshot.loop_running,
                loop_interval_seconds=snapshot.loop_interval_seconds,
            )
        )
        if include_events:
            events = env.get_recent_events()
            self.storage.append_events(events)
            for event in events:
                self.event_bus.publish(event)
        return snapshot

    def _compose_runtime_status(
        self,
        *,
        env: DundeeEnv,
        loop_running: bool,
        loop_interval_seconds: float,
    ) -> dict[str, Any]:
        return {
            "loop_running": bool(loop_running),
            "loop_interval_seconds": float(loop_interval_seconds),
            "runtime_mode": env.runtime_mode,
            "active_policy": env.policy_mode,
            "demand_multiplier": env.demand_multiplier,
            "warm_start_minutes": env.warm_start_minutes,
            "replay_year": env.replay_year,
            "replay_day": env.replay_day.isoformat(),
            "operational_start_ts": env.operational_start_time.isoformat(),
            "simulated_timestamp": env.current_time.isoformat(),
            "latest_external_request_id": env.latest_external_request_id,
            "active_request_count": sum(1 for request in env.requests.values() if request.status == "pending"),
            "queued_request_count": sum(1 for request in env.requests.values() if request.status == "queued"),
            "active_session_count": len(env.active_sessions),
            "completed_requests_total": env.completed_requests_total,
            "missed_requests_total": env.missed_requests_total,
        }

    def _resolve_start_options(
        self,
        *,
        replay_day: str,
        start_hour: int,
        start_minute: int,
        policy_mode: str | None,
        replay_year: int | None,
        runtime_mode: str | None,
        demand_multiplier: float | None,
        warm_start_hours: int,
        preset: str | None,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {
            "replay_day": replay_day,
            "start_hour": start_hour,
            "start_minute": start_minute,
            "policy_mode": policy_mode or self.config.default_policy,
            "replay_year": replay_year or self.config.replay_year,
            "runtime_mode": runtime_mode or self.config.default_runtime_mode,
            "demand_multiplier": demand_multiplier if demand_multiplier is not None else self.config.default_demand_multiplier,
            "warm_start_hours": warm_start_hours,
        }
        if preset == "busy_afternoon":
            options.update(
                {
                    "replay_day": "2024-06-10",
                    "start_hour": 15,
                    "start_minute": 0,
                    "policy_mode": "overload_aware",
                    "runtime_mode": "hybrid",
                    "demand_multiplier": 1.35,
                    "warm_start_hours": 4,
                }
            )
        return options

    def _build_target_start(self, replay_day: str, start_hour: int, start_minute: int) -> datetime:
        return datetime.fromisoformat(f"{replay_day}T00:00:00") + timedelta(
            hours=max(int(start_hour), 0),
            minutes=max(int(start_minute), 0),
        )


__all__ = ["RuntimeConfig", "RuntimeManager"]
