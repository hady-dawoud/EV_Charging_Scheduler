from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

import streamlit as st


DEFAULT_API_BASE = os.environ.get("DEMO_API_BASE_URL", "http://localhost:8000")


st.set_page_config(
    page_title="ZapRoute Demo Scenarios",
    page_icon="⚡",
    layout="wide",
)


def _api_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def _read_json_response(response: Any) -> Any:
    raw = response.read().decode("utf-8")
    if not raw:
        return None
    return json.loads(raw)


def get_json(base_url: str, path: str) -> Any:
    request = urllib.request.Request(
        _api_url(base_url, path),
        method="GET",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return _read_json_response(response)


def post_json(base_url: str, path: str, payload: dict[str, Any], token: str | None = None) -> Any:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        _api_url(base_url, path),
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return _read_json_response(response)


def api_call(label: str, fn):
    try:
        return fn(), None
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")
        except Exception:
            detail = str(exc)
        return None, f"{label} failed: HTTP {exc.code}: {detail}"
    except Exception as exc:
        return None, f"{label} failed: {exc}"


def option_metadata(option: dict[str, Any] | None) -> dict[str, Any]:
    if not option:
        return {}
    metadata = option.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def recommendation_options(recommendation: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not recommendation:
        return []

    options: list[dict[str, Any]] = []
    top = recommendation.get("top_recommendation")
    if isinstance(top, dict):
        top = dict(top)
        top["_role"] = "top"
        options.append(top)

    for alt in recommendation.get("alternatives") or []:
        if isinstance(alt, dict):
            alt = dict(alt)
            alt["_role"] = "alternative"
            options.append(alt)

    return options


def latest_recommendation(recent_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not recent_payload:
        return None
    recs = recent_payload.get("recommendations") or []
    if not recs:
        return None
    return recs[0]


def num(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def fmt_money(value: Any) -> str:
    try:
        return f"GBP {float(value):.3f}"
    except Exception:
        return "-"


def fmt_num(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def make_mobile_payload(
    *,
    preference_mode: str,
    connector_type: str,
    latitude: float,
    longitude: float,
    battery_level: float,
    target_battery_level: float,
    battery_kwh: float,
    latest_finish_minutes: int,
) -> dict[str, Any]:
    requested_energy_kwh = max(
        0.0,
        ((target_battery_level - battery_level) / 100.0) * battery_kwh,
    )

    return {
        "client_request_id": f"demo_{preference_mode}_{int(time.time() * 1000)}",
        "latitude": latitude,
        "longitude": longitude,
        "battery_level": battery_level,
        "target_battery_level": target_battery_level,
        "battery_kwh": battery_kwh,
        "vehicle_max_ac_kw": 11.0,
        "vehicle_max_dc_kw": 150.0,
        "requested_energy_kwh": requested_energy_kwh,
        "preference_mode": preference_mode,
        "connector_type": connector_type,
        "latest_finish_minutes_from_now": latest_finish_minutes,
        "zone_id": "zone_central_waterfront",
        "metadata": {
            "channel": "demo_dashboard",
            "scenario": "preference_mode_comparison",
        },
    }


def top_summary_row(rec: dict[str, Any]) -> dict[str, Any]:
    top = rec.get("top_recommendation") or {}
    meta = option_metadata(top)
    return {
        "Preference": (rec.get("metadata") or {}).get("preference_mode", "-"),
        "Top station": top.get("station_name", "-"),
        "Score": fmt_num(top.get("score"), 4),
        "Distance km": fmt_num(top.get("distance_km"), 3),
        "Wait min": top.get("estimated_wait_minutes", "-"),
        "Duration min": top.get("estimated_duration_minutes", "-"),
        "Cost": fmt_money(top.get("estimated_cost_gbp")),
        "Final price/kWh": fmt_money(meta.get("final_price_per_kwh")),
        "Multiplier": fmt_num(meta.get("total_dynamic_multiplier"), 3),
        "RL status": meta.get("rl_safety_status", "-"),
        "RL blocked": meta.get("rl_safety_blocked", "-"),
    }


def render_health(base_url: str) -> dict[str, Any] | None:
    health, err = api_call("health", lambda: get_json(base_url, "/health"))
    if err:
        st.error(err)
        return None

    cols = st.columns(5)
    cols[0].metric("API", health.get("status", "-"))
    cols[1].metric("Runtime", "started" if health.get("runtime_started") else "stopped")
    cols[2].metric("Loop", "running" if health.get("loop_running") else "stopped")
    cols[3].metric("Mode", health.get("runtime_mode", "-"))
    cols[4].metric("Active policy", health.get("active_policy", "-"))
    return health


def render_latest_header(rec: dict[str, Any] | None) -> None:
    if not rec:
        st.warning("No recent runtime recommendation found. Submit a request from the app or use the demo request button.")
        return

    top = rec.get("top_recommendation") or {}
    meta = rec.get("metadata") or {}
    top_meta = option_metadata(top)

    st.subheader("Latest runtime recommendation")
    cols = st.columns(4)
    cols[0].metric("Preference", meta.get("preference_mode", "-"))
    cols[1].metric("Effective policy", meta.get("effective_policy_name", "-"))
    cols[2].metric("Top station", top.get("station_name", "-"))
    cols[3].metric("Top score", fmt_num(top.get("score"), 4))

    proof = {
        "Mobile/runtime request": rec.get("client_request_id"),
        "Source type": rec.get("source_type"),
        "Policy source": meta.get("policy_source"),
        "RL filter applied": meta.get("rl_safety_filter_applied"),
        "RL candidates penalized": meta.get("rl_safety_candidates_penalized"),
        "RL candidates blocked": meta.get("rl_safety_candidates_blocked"),
        "Dynamic pricing enabled": top_meta.get("dynamic_pricing_enabled", meta.get("dynamic_pricing_enabled")),
    }
    st.json(proof, expanded=False)


def render_run_request_panel(base_url: str, token: str | None) -> None:
    st.subheader("Run a demo recommendation request")

    cols = st.columns(7)
    preference = cols[0].selectbox("Preference", ["cheapest", "fastest", "closest"], index=0)
    connector = cols[1].selectbox("Connector", ["Any", "ac", "rapid", "ultra_rapid"], index=0)
    battery = cols[2].number_input("Current %", min_value=0.0, max_value=100.0, value=35.0, step=5.0)
    target = cols[3].number_input("Target %", min_value=0.0, max_value=100.0, value=80.0, step=5.0)
    capacity = cols[4].number_input("Battery kWh", min_value=10.0, max_value=150.0, value=64.0, step=1.0)
    lat = cols[5].number_input("Lat", value=56.4590, format="%.6f")
    lon = cols[6].number_input("Lon", value=-2.9707, format="%.6f")

    payload = make_mobile_payload(
        preference_mode=preference,
        connector_type=connector,
        latitude=lat,
        longitude=lon,
        battery_level=battery,
        target_battery_level=target,
        battery_kwh=capacity,
        latest_finish_minutes=120,
    )

    if st.button("Run selected request"):
        if not token:
            st.error("Paste a bearer token in the sidebar to run /mobile/recommendations from this dashboard.")
        else:
            result, err = api_call(
                "mobile recommendation",
                lambda: post_json(base_url, "/mobile/recommendations", payload, token),
            )
            if err:
                st.error(err)
            else:
                st.success("Recommendation returned.")
                st.json(result, expanded=False)


def render_preference_modes(base_url: str, token: str | None, recent_payload: dict[str, Any] | None) -> None:
    st.subheader("Scenario 4: Cheapest / Fastest / Closest")

    st.caption("Proof: same request shape, different preference modes, runtime returns comparable top recommendations.")

    col_a, col_b, col_c = st.columns(3)
    connector = col_a.selectbox("Connector for comparison", ["Any", "ac", "rapid", "ultra_rapid"], index=0, key="pref_connector")
    battery = col_b.number_input("Current battery %", min_value=0.0, max_value=100.0, value=35.0, step=5.0, key="pref_battery")
    target = col_c.number_input("Target battery %", min_value=0.0, max_value=100.0, value=80.0, step=5.0, key="pref_target")

    if st.button("Run cheapest, fastest, closest"):
        if not token:
            st.error("Paste a bearer token in the sidebar first.")
        else:
            rows = []
            for preference in ["cheapest", "fastest", "closest"]:
                payload = make_mobile_payload(
                    preference_mode=preference,
                    connector_type=connector,
                    latitude=56.4590,
                    longitude=-2.9707,
                    battery_level=battery,
                    target_battery_level=target,
                    battery_kwh=64.0,
                    latest_finish_minutes=120,
                )
                result, err = api_call(
                    f"{preference} recommendation",
                    lambda payload=payload: post_json(base_url, "/mobile/recommendations", payload, token),
                )
                if err:
                    st.error(err)
                    continue
                rows.append(top_summary_row(result))
            if rows:
                st.dataframe(rows, use_container_width=True, hide_index=True)

    recs = (recent_payload or {}).get("recommendations") or []
    latest_by_pref: dict[str, dict[str, Any]] = {}
    for rec in recs:
        meta = rec.get("metadata") or {}
        pref = meta.get("preference_mode")
        if pref and pref not in latest_by_pref:
            latest_by_pref[pref] = rec

    rows = [top_summary_row(rec) for _, rec in sorted(latest_by_pref.items())]
    if rows:
        st.markdown("Latest observed app/runtime results by preference")
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("No observed preference-mode recommendations yet.")


def render_dynamic_pricing(rec: dict[str, Any] | None) -> None:
    st.subheader("Scenario 3: Dynamic pricing multiplier")

    options = recommendation_options(rec)
    if not options:
        st.warning("No recommendation options available.")
        return

    rows = []
    for option in options:
        meta = option_metadata(option)
        rows.append(
            {
                "Role": option.get("_role"),
                "Station": option.get("station_name"),
                "Cost": fmt_money(option.get("estimated_cost_gbp")),
                "Base price/kWh": fmt_money(meta.get("base_price_per_kwh")),
                "Multiplier": fmt_num(meta.get("total_dynamic_multiplier"), 3),
                "Final price/kWh": fmt_money(meta.get("final_price_per_kwh")),
                "Reason": meta.get("pricing_reason", "-"),
                "Load ratio": fmt_num(meta.get("transformer_load_ratio"), 4),
                "Headroom ratio": fmt_num(meta.get("transformer_headroom_ratio"), 4),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    top_meta = option_metadata(options[0])
    st.success(
        "Proof: runtime returns base price, multiplier, final price, and pricing reason."
    )
    st.json(
        {
            "base_price_per_kwh": top_meta.get("base_price_per_kwh"),
            "total_dynamic_multiplier": top_meta.get("total_dynamic_multiplier"),
            "final_price_per_kwh": top_meta.get("final_price_per_kwh"),
            "pricing_reason": top_meta.get("pricing_reason"),
            "dynamic_pricing_enabled": top_meta.get("dynamic_pricing_enabled"),
        },
        expanded=False,
    )


def render_rl_safety(rec: dict[str, Any] | None) -> None:
    st.subheader("Scenario 2 / 5: Grid safety and RL penalty influence")

    if not rec:
        st.warning("No recent recommendation available.")
        return

    response_meta = rec.get("metadata") or {}
    options = recommendation_options(rec)

    cols = st.columns(5)
    cols[0].metric("Effective policy", response_meta.get("effective_policy_name", "-"))
    cols[1].metric("RL applied", str(response_meta.get("rl_safety_filter_applied", "-")))
    cols[2].metric("Penalized", response_meta.get("rl_safety_candidates_penalized", "-"))
    cols[3].metric("Blocked", response_meta.get("rl_safety_candidates_blocked", "-"))
    cols[4].metric("Final ranker", response_meta.get("final_ranker", "-"))

    rows = []
    for option in options:
        meta = option_metadata(option)
        rows.append(
            {
                "Role": option.get("_role"),
                "Station": option.get("station_name"),
                "Base score": fmt_num(meta.get("base_preference_score"), 4),
                "RL penalty": fmt_num(meta.get("rl_safety_penalty"), 4),
                "Penalty weight": fmt_num(meta.get("rl_safety_penalty_weight"), 3),
                "Adjusted score": fmt_num(meta.get("rl_safety_adjusted_score", option.get("score")), 4),
                "Status": meta.get("rl_safety_status", "-"),
                "Blocked": meta.get("rl_safety_blocked", "-"),
                "Reason": meta.get("rl_safety_reason", "-"),
                "Action index": meta.get("rl_selected_action_index", "-"),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.success(
        "Proof: the runtime applies RL-safety metadata and penalty-adjusted scoring before results are displayed."
    )
    st.json(
        {
            "rl_policy_fail_closed": response_meta.get("rl_policy_fail_closed"),
            "rl_feeder_checkpoint_path": response_meta.get("rl_feeder_checkpoint_path"),
            "feeder_context_available": response_meta.get("feeder_context_available"),
            "grid_advisory_available": response_meta.get("grid_advisory_available"),
            "rl_selected_action_index": response_meta.get("rl_selected_action_index"),
            "rl_safety_filter_applied": response_meta.get("rl_safety_filter_applied"),
            "rl_safety_filter_reason": response_meta.get("rl_safety_filter_reason"),
        },
        expanded=False,
    )


def render_availability(rec: dict[str, Any] | None) -> None:
    st.subheader("Scenario 1: Connector availability / CP count")

    options = recommendation_options(rec)
    if not options:
        st.warning("No recommendation options available.")
        return

    rows = []
    for option in options:
        meta = option_metadata(option)
        rows.append(
            {
                "Role": option.get("_role"),
                "Station": option.get("station_name"),
                "Compatible": option.get("charger_compatible"),
                "Queue": option.get("current_queue"),
                "Utilization": fmt_num(option.get("utilization"), 4),
                "Connector type": meta.get("selected_connector_type", "-"),
                "Connector power kW": meta.get("selected_connector_power_kw", "-"),
                "Connector ID": meta.get("selected_connector_id", "-"),
                "Effective power kW": meta.get("effective_power_kw", "-"),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)
    st.info(
        "For the full CP-count demo, use the scenario script to occupy all matching ultra rapid connectors, then refresh this table and confirm that the full station is absent from returned recommendations."
    )


def render_full_flow_hint(rec: dict[str, Any] | None) -> None:
    st.subheader("Scenario 6: Full app workflow proof")

    if not rec:
        st.warning("No recommendation observed yet.")
        return

    top = rec.get("top_recommendation") or {}
    st.markdown(
        f"""
        Current proof chain:

        1. App/API returned a runtime recommendation.
        2. Top station: **{top.get("station_name", "-")}**
        3. Reserve this station in the mobile app.
        4. Confirm start.
        5. Stop charging.
        6. Verify final session cost against runtime-derived price in the DB.
        """
    )


st.title("ZapRoute Demo Scenarios")
st.caption("Focused dashboard for showing that the mobile app is connected to runtime recommendation, pricing, and RL-safety logic.")

with st.sidebar:
    st.header("Demo controls")
    api_base = st.text_input("API base URL", DEFAULT_API_BASE)
    token = st.text_area("Bearer token for /mobile/recommendations", value="", height=90)
    token = token.strip() or None
    limit = st.slider("Recent recommendation limit", min_value=1, max_value=50, value=20)

    st.markdown("---")
    refresh = st.button("Refresh")

if refresh:
    st.rerun()

health = render_health(api_base)

recent_payload, recent_err = api_call(
    "recent recommendations",
    lambda: get_json(api_base, f"/runtime/recommendations/recent?limit={limit}"),
)
if recent_err:
    st.error(recent_err)
    recent_payload = None

rec = latest_recommendation(recent_payload)
render_latest_header(rec)

tabs = st.tabs(
    [
        "Run request",
        "Preference modes",
        "Dynamic pricing",
        "RL safety",
        "CP availability",
        "Full workflow",
        "Raw latest",
    ]
)

with tabs[0]:
    render_run_request_panel(api_base, token)

with tabs[1]:
    render_preference_modes(api_base, token, recent_payload)

with tabs[2]:
    render_dynamic_pricing(rec)

with tabs[3]:
    render_rl_safety(rec)

with tabs[4]:
    render_availability(rec)

with tabs[5]:
    render_full_flow_hint(rec)

with tabs[6]:
    st.json(rec or {}, expanded=False)
