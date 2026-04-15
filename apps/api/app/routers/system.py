from fastapi import APIRouter, HTTPException, Query

from app.services.runtime_service import (
    RuntimeNotStartedError,
    get_recent_events,
    get_recent_recommendations,
    get_runtime_state,
    get_runtime_status,
)

router = APIRouter(tags=["system"])


@router.get("/")
def root():
    return {"message": "EV Smart Charging API is running"}


@router.get("/health")
def health():
    status = get_runtime_status()
    runtime_started = False
    try:
        state = get_runtime_state()
        runtime_started = True
        simulated_timestamp = state.simulated_timestamp
    except RuntimeNotStartedError:
        simulated_timestamp = None

    return {
        "status": "ok",
        "runtime_started": runtime_started,
        "loop_running": bool(status.get("loop_running", False)),
        "runtime_mode": status.get("runtime_mode"),
        "active_policy": status.get("active_policy"),
        "simulated_timestamp": simulated_timestamp,
    }


@router.get("/runtime/status")
def runtime_status():
    return get_runtime_status()


@router.get("/runtime/state")
def runtime_state():
    try:
        return get_runtime_state()
    except RuntimeNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runtime/events")
def runtime_events(limit: int = Query(default=50, ge=1, le=200)):
    try:
        return {"events": get_recent_events(limit=limit)}
    except RuntimeNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/runtime/recommendations/recent")
def runtime_recent_recommendations(
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        return {"recommendations": get_recent_recommendations(limit=limit)}
    except RuntimeNotStartedError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc