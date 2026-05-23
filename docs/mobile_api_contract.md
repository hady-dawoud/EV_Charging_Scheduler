# Mobile API Contract - EV Smart Charging App

## 1. Purpose

This document defines the API contract used by the production mobile app and the local web development harness.

The mobile app talks only to the FastAPI backend. It must not talk directly to PostgreSQL, Docker, the simulator runtime, or charger-event endpoints.

Production-style lifecycle:

~~~
Mobile user creates reservation
Backend stores reservation
Charger/simulator/admin event starts session
Charger/simulator/admin event completes session
Mobile only displays reservation/session lifecycle state
~~~

---

## 2. Base URLs

Android emulator:

~~~
http://10.0.2.2:8000
~~~

Local web development:

~~~
http://localhost:8000
~~~

Local physical phone:

~~~
http://<computer-lan-ip>:8000
~~~

Deployed backend through reverse proxy:

~~~
http://smartevcharging.uaenorth.cloudapp.azure.com/api
~~~

---

## 3. Auth endpoints

### Register

~~~
POST /auth/register
~~~

Request:

~~~json
{
  "full_name": "Mobile User",
  "email": "mobile.user@example.com",
  "password": "password123"
}
~~~

Response:

~~~json
{
  "access_token": "jwt_access_token",
  "refresh_token": "opaque_refresh_token",
  "token_type": "bearer",
  "user": {
    "id": "uuid",
    "full_name": "Mobile User",
    "email": "mobile.user@example.com"
  }
}
~~~

Mobile behavior:

- Save access token in memory.
- Save refresh token in secure storage.
- Navigate to main app after success.
- Show validation errors from `422`.

### Login

~~~
POST /auth/login
~~~

Request:

~~~json
{
  "email": "mobile.user@example.com",
  "password": "password123",
  "device_id": "mobile-app"
}
~~~

Response shape matches register.

### Refresh token

~~~
POST /auth/refresh
~~~

Request:

~~~json
{
  "refresh_token": "opaque_refresh_token",
  "device_id": "mobile-app"
}
~~~

Response shape matches register/login token response.

---

## 4. System endpoint

### Health

~~~
GET /health
~~~

Response:

~~~json
{
  "status": "ok",
  "runtime_started": true,
  "loop_running": true,
  "runtime_mode": "hybrid",
  "active_policy": "overload_aware",
  "simulated_timestamp": "2024-06-16T23:45:00"
}
~~~

Mobile behavior:

- Use for backend/runtime availability checks.
- Do not crash if unavailable.
- Do not retry aggressively.

---

## 5. Recommendations

### Mobile recommendations

~~~
POST /mobile/recommendations
Authorization: Bearer <access_token>
~~~

Request:

~~~json
{
  "target_soc": 80,
  "preference_mode": "cheapest",
  "charger_type": "any"
}
~~~

Accepted values:

~~~
preference_mode: cheapest | fastest | closest
charger_type: any | ac | dc
~~~

Response:

~~~json
{
  "request_id": "external_abc123",
  "client_request_id": "mobile_abc123",
  "simulated_timestamp": "2024-06-21T11:30:00",
  "zone_id": "zone_central_waterfront",
  "top_recommendation": {
    "station_id": "gellatly_street_car_park_dundee",
    "station_name": "Gellatly Street Car Park, Dundee",
    "zone_id": "zone_central_waterfront",
    "transformer_id": "tx_central_waterfront",
    "score": 0.7469,
    "distance_km": 0.645,
    "estimated_wait_minutes": 0,
    "estimated_duration_minutes": 30,
    "estimated_cost_gbp": 17.326,
    "transformer_headroom_kw": 515.753,
    "current_queue": 0,
    "utilization": 0.2222,
    "charger_compatible": true,
    "reason_tags": ["nearby", "low_wait", "high_headroom"],
    "metadata": {
      "selected_connector_type": "rapid",
      "selected_connector_power_kw": 50.0
    }
  },
  "alternatives": [],
  "congestion_note": null,
  "debug_reasoning_summary": "",
  "source_type": "external_live",
  "metadata": {}
}
~~~

Mobile behavior:

- Use `top_recommendation` as primary recommendation.
- Use `alternatives` as alternative cards.
- Preserve `request_id`, `client_request_id`, selected `station_id`, and selected rank for reservation.
- Do not calculate recommendations locally.
- Do not automatically retry this POST request because duplicate live requests can pollute the simulator runtime.

---

## 6. Reservations

### Create reservation

~~~
POST /reservations
Authorization: Bearer <access_token>
~~~

Request:

~~~json
{
  "station_id": "gellatly_street_car_park_dundee",
  "client_request_id": "mobile_abc123",
  "request_id": "external_abc123",
  "recommendation_rank": 1,
  "reserved_start_at": "2026-05-23T19:30:00Z",
  "reserved_until": "2026-05-23T20:00:00Z",
  "estimated_cost_gbp": 17.326,
  "estimated_duration_minutes": 30,
  "charger_label": "rapid",
  "distance_km": 0.645,
  "score": 0.7469
}
~~~

Response:

~~~json
{
  "reservation_id": "uuid",
  "user_id": "uuid",
  "station_id": "gellatly_street_car_park_dundee",
  "station_name": "Gellatly Street Car Park, Dundee",
  "client_request_id": "mobile_abc123",
  "request_id": "external_abc123",
  "recommendation_rank": 1,
  "status": "confirmed",
  "reserved_start_at": "2026-05-23T19:30:00Z",
  "reserved_until": "2026-05-23T20:00:00Z",
  "cancelled_at": null,
  "estimated_cost_gbp": 17.326,
  "estimated_duration_minutes": 30,
  "charger_label": "rapid",
  "distance_km": 0.645,
  "score": 0.7469,
  "created_at": "2026-05-23T19:10:00Z"
}
~~~

Mobile behavior:

- Show confirmation screen after success.
- Store no local-only reservation state.
- Read reservation history from backend.

### List my reservations

~~~
GET /reservations/me
Authorization: Bearer <access_token>
~~~

Response:

~~~json
{
  "reservations": []
}
~~~

Backend behavior:

- Reconciles expired confirmed reservations.
- Confirmed reservations past `reserved_until + grace period` become `expired`.

### Cancel reservation

~~~
PATCH /reservations/{reservation_id}/cancel
Authorization: Bearer <access_token>
~~~

Mobile behavior:

- Use only if cancellation UI is added.
- Cancelled reservations should no longer appear as waiting reservations.

---

## 7. Charging sessions

Mobile can only read charging sessions.

Mobile must not start or complete sessions directly.

### List my charging sessions

~~~
GET /sessions/me
Authorization: Bearer <access_token>
~~~

Response:

~~~json
{
  "sessions": [
    {
      "session_id": "uuid",
      "status": "completed",
      "station_id": "gellatly_street_car_park_dundee",
      "station_name": "Gellatly Street Car Park, Dundee",
      "reservation_id": "uuid",
      "client_request_id": "mobile_abc123",
      "request_id": "external_abc123",
      "started_at": "2026-05-23T19:10:25Z",
      "ended_at": "2026-05-23T19:40:25Z",
      "energy_kwh": 18.5,
      "cost_total": 7.4,
      "connector_type": "rapid",
      "charger_power_kw": 50.0,
      "created_at": "2026-05-23T19:10:25Z"
    }
  ]
}
~~~

Backend behavior:

- Reconciles stale active sessions.
- Active sessions older than estimated duration plus grace become `stale_active`.
- If no estimate exists, default stale threshold applies.

### Get active charging session

~~~
GET /sessions/active
Authorization: Bearer <access_token>
~~~

Response:

~~~json
{
  "session": null
}
~~~

or:

~~~json
{
  "session": {
    "session_id": "uuid",
    "status": "active",
    "station_id": "gellatly_street_car_park_dundee",
    "station_name": "Gellatly Street Car Park, Dundee",
    "reservation_id": "uuid",
    "client_request_id": "mobile_abc123",
    "request_id": "external_abc123",
    "started_at": "2026-05-23T19:10:25Z",
    "ended_at": null,
    "energy_kwh": 0,
    "cost_total": null,
    "connector_type": "rapid",
    "charger_power_kw": 50.0,
    "created_at": "2026-05-23T19:10:25Z"
  }
}
~~~

---

## 8. Internal charger-event endpoints

These endpoints are not for the mobile app UI.

They represent charger/provider/simulator/admin events.

Authentication:

~~~
X-Charger-Event-Secret: <internal-secret>
~~~

### Start session from charger event

~~~
POST /charger-events/sessions/start
~~~

Request:

~~~json
{
  "reservation_id": "uuid",
  "started_at": "2026-05-23T19:10:25Z",
  "connector_type": "rapid",
  "charger_power_kw": 50.0
}
~~~

Response:

~~~json
{
  "session_id": "uuid",
  "status": "active",
  "station_id": "gellatly_street_car_park_dundee",
  "station_name": "Gellatly Street Car Park, Dundee",
  "reservation_id": "uuid",
  "client_request_id": "mobile_abc123",
  "request_id": "external_abc123",
  "started_at": "2026-05-23T19:10:25Z",
  "ended_at": null,
  "energy_kwh": 0,
  "cost_total": null,
  "connector_type": "rapid",
  "charger_power_kw": 50,
  "created_at": "2026-05-23T19:10:25Z"
}
~~~

Failure cases:

~~~
401 invalid charger event secret
404 reservation not found
409 reservation cancelled
409 reservation expired
409 reservation already completed
~~~

### Complete session from charger event

~~~
POST /charger-events/sessions/{session_id}/complete
~~~

Request:

~~~json
{
  "ended_at": "2026-05-23T19:40:25Z",
  "energy_kwh": 18.5,
  "cost_total": 7.4
}
~~~

Failure cases:

~~~
401 invalid charger event secret
404 session not found
409 session already completed
~~~

---

## 9. Lifecycle statuses

Reservation statuses:

~~~
confirmed
active
completed
cancelled
expired
~~~

Charging session statuses:

~~~
active
completed
stale_active
~~~

Mobile display rules:

~~~
confirmed reservation without linked session -> Reserved Options
active session -> Active Charging
completed session -> Completed Charging
expired/cancelled reservation -> Attention Needed
stale_active session -> Attention Needed
~~~

---

## 10. Security rules

- JWT protects user endpoints.
- Refresh tokens are opaque and stored securely.
- Charger-event secret protects internal charger/simulator endpoints.
- Mobile app must not include charger-event secret.
- Mobile app must not call `/charger-events/*`.
- Deployed production should replace all default secrets.

---

## 11. Error handling

Mobile should handle:

~~~
400 bad request
401 unauthorized / token expired
403 forbidden
404 not found
409 lifecycle conflict
422 validation error
500 backend error
~~~

Behavior:

- Show user-readable message.
- Do not expose stack traces.
- Do not retry non-idempotent POST requests automatically.
- For token expiry, try refresh once, then sign out if refresh fails.

---

## 12. Smoke-test expectation

A valid local lifecycle smoke test should verify:

~~~
register/login
create reservation
charger event starts session
sessions/me shows active/completed state
charger event completes session
expired reservation blocks charger start
stale active session reconciles to stale_active
~~~
