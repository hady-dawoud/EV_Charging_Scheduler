# Mobile API Contract - EV Smart Charging App v0.1.6

**Last updated:** 2026-06-09  
**Code baseline checked:** uploaded `apps/api` files and Android `build.gradle` from 2026-06-09  
**Latest tested APK baseline:** `ev-smart-charging-v0.1.6.apk`  
**Android build metadata:** `versionName "0.1.6"`, `versionCode 7`

---

## 1. Purpose

This document defines the API contract used by the EV Smart Charging mobile app and the local web development harness.

The mobile app talks only to the FastAPI backend. It must not talk directly to PostgreSQL, Docker, the simulator runtime, or internal charger-event endpoints.

Production-style lifecycle:

```text
Mobile user creates reservation
Backend stores reservation
Charger/simulator/admin event starts session
Charger/simulator/admin event completes session
Mobile displays reservation/session lifecycle state
```

Important implementation note:

- The backend still exposes authenticated user session mutation endpoints: `POST /sessions` and `PATCH /sessions/{session_id}/complete`.
- Product/demo rule remains: the mobile UI should not manually start or complete charging sessions in the normal user journey.
- Internal charger-event endpoints are the preferred source of charging lifecycle state for the production-style flow.

---

## 2. Base URLs

Android emulator:

```text
http://10.0.2.2:8000
```

Local web development:

```text
http://localhost:8000
```

Local physical phone:

```text
http://<computer-lan-ip>:8000
```

Deployed backend through reverse proxy:

```text
https://smartevcharging.uaenorth.cloudapp.azure.com/api
```

FastAPI is configured with `root_path="/api"`, so public reverse-proxy requests use the `/api` prefix while app routers are defined without duplicating that prefix.

---

## 3. Auth model

Auth uses:

- JWT access tokens.
- Opaque refresh tokens stored server-side as hashes.
- Refresh-token rotation on refresh.
- Logout by refresh token only.
- Google ID-token login through `POST /auth/google`.
- Password reset tokens stored as hashes and consumed once.

Common user object:

```json
{
  "id": "uuid",
  "full_name": "Mobile User",
  "email": "mobile.user@example.com"
}
```

Common auth response for register, email/password login, and Google login:

```json
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
```

Mobile token behavior:

- Keep access token in app memory/state.
- Store refresh token in secure storage: Keychain on native, localStorage wrapper on web.
- On `401`, attempt refresh once, retry the protected request once, then sign out if refresh fails.
- Do not expose raw JWT/refresh tokens in logs.

---

## 4. Auth endpoints

### Register

```text
POST /auth/register
```

Request:

```json
{
  "full_name": "Mobile User",
  "email": "mobile.user@example.com",
  "password": "password123"
}
```

Validation:

```text
full_name: required, 2-255 chars
email: valid email
password: required, 8-128 chars
extra fields: forbidden
```

Response:

```text
201 AuthResponse
```

Failure cases:

```text
409 email already registered
422 validation error
```

Mobile behavior:

- Save returned tokens.
- Navigate to main app after success.
- Show user-readable validation or duplicate-email message.

### Login with email/password

```text
POST /auth/login
```

Request:

```json
{
  "email": "mobile.user@example.com",
  "password": "password123",
  "device_id": "mobile-app"
}
```

Validation:

```text
email: valid email
password: required, 1-128 chars
device_id: optional, max 255 chars
extra fields: forbidden
```

Response:

```text
200 AuthResponse
```

Failure cases:

```text
401 invalid email or password
403 inactive user
422 validation error
```

### Login/sign up with Google

```text
POST /auth/google
```

Request:

```json
{
  "id_token": "google_id_token_from_client",
  "device_id": "mobile-app"
}
```

Validation:

```text
id_token: required, min 20 chars
device_id: optional, max 255 chars
extra fields: forbidden
```

Response:

```text
200 AuthResponse
```

Backend behavior:

- Requires `GOOGLE_WEB_CLIENT_ID` / `google_web_client_id` to be configured.
- Verifies the supplied Google ID token against the configured Google web client ID.
- Requires Google `sub`, email, and verified email.
- Uses `name` from Google as full name if available; otherwise uses the email local part.
- If `google_sub` already exists, logs in that user.
- If email exists without `google_sub`, links the Google subject to that existing account.
- If no account exists, creates a new Google-linked account with a generated internal password hash.

Failure cases:

```text
401 Google login not configured
401 invalid Google ID token
401 Google account email is not verified
403 inactive user
422 validation error
```

Mobile behavior:

- Send the backend a Google **ID token**, not an access token.
- Treat the response exactly like normal login/register and store both tokens.
- Use this endpoint for both “Continue with Google” and the Google sign-up entry point.

### Refresh token

```text
POST /auth/refresh
```

Request:

```json
{
  "refresh_token": "opaque_refresh_token",
  "device_id": "mobile-app"
}
```

Validation:

```text
refresh_token: required, min 20 chars
device_id: optional, max 255 chars
extra fields: forbidden
```

Response:

```json
{
  "access_token": "new_jwt_access_token",
  "refresh_token": "new_opaque_refresh_token",
  "token_type": "bearer"
}
```

Important: refresh response does **not** include the `user` object.

Backend behavior:

- Hashes the supplied refresh token and looks up an active record.
- Rejects missing, revoked, or expired refresh tokens.
- Revokes the old refresh token.
- Issues a new access token and refresh token.

Failure cases:

```text
401 invalid refresh token
401 refresh token expired
403 inactive user
422 validation error
```

### Logout

```text
POST /auth/logout
```

Request:

```json
{
  "refresh_token": "opaque_refresh_token"
}
```

Response:

```json
{
  "success": true
}
```

Backend behavior:

- Hashes and revokes the refresh token if active.
- Does not require a bearer access token.
- Returns success even if the token is already absent/revoked from the user perspective.

Mobile behavior:

- Call logout with the stored refresh token.
- Clear access token and refresh token locally regardless of response details.

### Get current user

```text
GET /auth/me
Authorization: Bearer <access_token>
```

Response:

```json
{
  "id": "uuid",
  "full_name": "Mobile User",
  "email": "mobile.user@example.com"
}
```

Failure cases:

```text
401 missing bearer token
401 invalid token
401 invalid token type
401 invalid token subject
403 inactive user
```

---

## 5. Password reset endpoints

### Request password reset

```text
POST /auth/password-reset/request
```

Request:

```json
{
  "email": "mobile.user@example.com"
}
```

Response:

```json
{
  "success": true,
  "message": "If an account exists for that email, password reset instructions have been generated.",
  "development_reset_token": null
}
```

Backend behavior:

- Always returns a generic success message so account existence is not exposed.
- If the user exists and is active, creates a short-lived reset token.
- Stores only the token hash in `password_reset_tokens`.
- If email sending is enabled, sends a reset URL in this shape:

```text
<PASSWORD_RESET_WEB_URL>/?reset_token=<url-encoded-token>
```

Configuration knobs:

```text
password_reset_token_expire_minutes: default 30
password_reset_email_enabled: default false unless VM env enables it
password_reset_return_token_for_development: default true in code; should be false outside dev/demo token-copy mode
password_reset_web_url: default https://smartevcharging.uaenorth.cloudapp.azure.com
```

Release behavior note:

- v0.1.6 uses reset-link email UX.
- If `development_reset_token` is still returned in any non-local deployment, disable it with the VM environment config.
- If the sender is `onboarding@resend.dev`, treat email delivery as development/testing until a verified sending domain is configured.

### Confirm password reset

```text
POST /auth/password-reset/confirm
```

Request:

```json
{
  "token": "reset_token_from_email_link",
  "new_password": "newpassword123"
}
```

Validation:

```text
token: required, min 20 chars
new_password: required, 8-128 chars
extra fields: forbidden
```

Response:

```json
{
  "success": true
}
```

Backend behavior:

- Hashes the supplied token.
- Rejects invalid, expired, or already-used tokens.
- Updates the user password hash.
- Marks the reset token as used.
- Revokes all active refresh tokens for the user.

Failure cases:

```text
400 invalid or already used password reset token
400 password reset token expired
403 inactive user
422 validation error
```

Mobile/web behavior:

- Forgot Password screen requests reset by email.
- Reset Password screen should read `reset_token` from the email link and avoid requiring manual token copy/paste.
- Hide the token field when the screen is opened from a reset-link URL.

---

## 6. Vehicle profile endpoints

### Get current user's vehicle

```text
GET /vehicles/me
Authorization: Bearer <access_token>
```

Response:

```json
{
  "id": "uuid",
  "make": "Tesla",
  "model": "Model 3 LR",
  "battery_capacity_kwh": 82.0,
  "current_soc": 45.0,
  "range_km": 225.0
}
```

Backend behavior:

- If the user has no vehicle row, creates and returns a default vehicle profile:

```json
{
  "make": "Tesla",
  "model": "Model 3 LR",
  "battery_capacity_kwh": 82.0,
  "current_soc": 45.0,
  "range_km": 225.0
}
```

### Upsert current user's vehicle

```text
PUT /vehicles/me
Authorization: Bearer <access_token>
```

Request:

```json
{
  "make": "Tesla",
  "model": "Model 3 LR",
  "battery_capacity_kwh": 82.0,
  "current_soc": 55.0,
  "range_km": 275.0
}
```

Validation:

```text
make: required, 1-120 chars
model: required, 1-120 chars
battery_capacity_kwh: > 0 and <= 250
current_soc: 0-100
range_km: 0-2000
extra fields: forbidden
```

Response shape matches `GET /vehicles/me`.

Mobile mapping:

```text
battery_capacity_kwh -> batteryCapacity
current_soc -> currentSoC
range_km -> rangeLeft
```

Mobile behavior:

- Home battery ring should reflect saved `current_soc`.
- Charging Request should use saved `current_soc` and `battery_capacity_kwh` where applicable.

---

## 7. System endpoints

### Health

```text
GET /health
```

Response:

```json
{
  "status": "ok",
  "runtime_started": true,
  "loop_running": true,
  "runtime_mode": "hybrid",
  "active_policy": "overload_aware",
  "simulated_timestamp": "2024-06-16T23:45:00"
}
```

Mobile behavior:

- Use for backend/runtime availability checks if needed.
- Do not crash if unavailable.
- Do not retry aggressively.

Other runtime endpoints exist for dashboard/operator/debug use, not normal mobile UI:

```text
GET /runtime/status
GET /runtime/state
GET /runtime/events
GET /runtime/recommendations/recent
```

---

## 8. Recommendations

### Mobile recommendations

```text
POST /mobile/recommendations
Authorization: Bearer <access_token>
```

Request:

```json
{
  "client_request_id": "mobile_abc123",
  "latitude": 56.462,
  "longitude": -2.9707,
  "battery_level": 45,
  "target_battery_level": 80,
  "battery_kwh": 82,
  "vehicle_profile_id": "uuid-or-profile-key",
  "vehicle_max_ac_kw": 11,
  "vehicle_max_dc_kw": 150,
  "requested_energy_kwh": null,
  "preference_mode": "cheapest",
  "connector_type": "Any",
  "latest_finish_minutes_from_now": 90,
  "zone_id": null,
  "metadata": {}
}
```

Validation/defaults:

```text
client_request_id: optional, max 255 chars
latitude: optional float
longitude: optional float
battery_level: optional, 0-100
target_battery_level: optional, 0-100
battery_kwh: optional, default 60.0, > 0
vehicle_profile_id: optional, max 255 chars
vehicle_max_ac_kw: optional, default 11.0, >= 0
vehicle_max_dc_kw: optional, default 150.0, >= 0
requested_energy_kwh: optional, >= 0
preference_mode: closest | cheapest | fastest, default fastest; normalized by backend
connector_type: string, default Any, max 100 chars
latest_finish_minutes_from_now: default 90, 5-1440
zone_id: optional, max 255 chars
metadata: object, default {}
extra fields: forbidden
```

Additional backend rule:

```text
If both battery_level and target_battery_level are supplied, target_battery_level must be greater than battery_level.
```

Failure cases:

```text
400 target battery level must be greater than current battery level
401 missing/invalid bearer token
409 simulator runtime is not started
422 validation error
```

Backend mapping into simulator/runtime request:

```text
battery_level -> current_soc
target_battery_level -> target_soc
battery_kwh -> battery_kwh
connector_type -> charger_type
latest_finish_minutes_from_now -> latest_finish_ts
metadata.source -> mobile_app
metadata.user_id -> current user id
source_type -> external_live
```

Response is the shared simulator `RecommendationResponse`, with typical fields:

```json
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
```

Mobile behavior:

- Use `top_recommendation` as the primary recommendation.
- Use `alternatives` as alternative cards.
- Preserve `request_id`, `client_request_id`, selected `station_id`, and selected rank for reservation.
- Do not calculate recommendations locally.
- Do not automatically retry this POST request because duplicate live requests can pollute runtime/request history.

### Live external recommendations

```text
POST /recommendations
```

This accepts the lower-level `ExternalChargingRequest` contract from `ev_core`. It is for simulator/runtime integration and debugging, not the normal mobile UI path.

---

## 9. Reservations

### Create reservation

```text
POST /reservations
Authorization: Bearer <access_token>
```

Request:

```json
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
```

Validation/defaults:

```text
station_id: required, 2-255 chars
client_request_id: optional, max 255 chars
request_id: optional, max 255 chars
recommendation_rank: optional, >= 1
reserved_start_at: required datetime
reserved_until: optional datetime; defaults to reserved_start_at + 15 minutes
estimated_cost_gbp: optional, >= 0
estimated_duration_minutes: optional, >= 0
charger_label: optional, max 100 chars
distance_km: optional, >= 0
score: optional float
extra fields: forbidden
```

Response:

```json
{
  "reservation_id": "uuid",
  "status": "confirmed",
  "station_id": "gellatly_street_car_park_dundee",
  "station_name": "Gellatly Street Car Park, Dundee",
  "client_request_id": "mobile_abc123",
  "request_id": "external_abc123",
  "recommendation_rank": 1,
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
```

Failure cases:

```text
401 missing/invalid bearer token
404 station not found
422 validation error
```

Mobile behavior:

- Show confirmation screen after success.
- Store no local-only reservation state as source of truth.
- Read reservation history from backend.

### List my reservations

```text
GET /reservations/me
Authorization: Bearer <access_token>
```

Response:

```json
{
  "reservations": []
}
```

Backend behavior:

- Reconciles expired confirmed reservations.
- Confirmed reservations past `reserved_until + 10 minutes` become `expired`.

### Cancel reservation

```text
PATCH /reservations/{reservation_id}/cancel
Authorization: Bearer <access_token>
```

Response:

```json
{
  "reservation_id": "uuid",
  "status": "cancelled"
}
```

Failure cases:

```text
404 reservation not found
409 reservation already cancelled
```

Mobile behavior:

- Use only if cancellation UI is enabled.
- Cancelled reservations should no longer appear as waiting reservations.

---

## 10. Charging sessions

Normal mobile UI should read sessions only. Charging lifecycle should be changed by internal charger/simulator/admin events.

### List my charging sessions

```text
GET /sessions/me
Authorization: Bearer <access_token>
```

Optional query:

```text
?status=active
?status=completed
?status=stale_active
```

Response:

```json
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
```

Backend behavior:

- Reconciles stale active sessions before returning data.
- Active sessions older than `estimated_duration_minutes + 30 minutes` become `stale_active`.
- If no estimate exists, the default stale threshold is 180 minutes.

### Get active charging session

```text
GET /sessions/active
Authorization: Bearer <access_token>
```

Response when no active session:

```json
{
  "session": null
}
```

Response when active:

```json
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
```

### User-auth session mutation endpoints present in backend

These endpoints exist in code but should not be used by the normal mobile product journey unless deliberately enabling a demo/admin/manual flow.

#### Start charging session

```text
POST /sessions
Authorization: Bearer <access_token>
```

Request:

```json
{
  "station_id": "gellatly_street_car_park_dundee",
  "reservation_id": "uuid",
  "client_request_id": "mobile_abc123",
  "request_id": "external_abc123",
  "started_at": "2026-05-23T19:10:25Z",
  "connector_type": "rapid",
  "charger_power_kw": 50.0
}
```

#### Complete charging session

```text
PATCH /sessions/{session_id}/complete
Authorization: Bearer <access_token>
```

Request:

```json
{
  "ended_at": "2026-05-23T19:40:25Z",
  "energy_kwh": 18.5,
  "cost_total": 7.4
}
```

Documentation rule:

- Keep these documented as backend-present endpoints.
- Keep product wording clear that mobile users should not manually control charging lifecycle in the intended production-style flow.

---

## 11. Internal charger-event endpoints

These endpoints are not for the mobile app UI. They represent charger/provider/simulator/admin events.

Authentication:

```text
X-Charger-Event-Secret: <internal-secret>
```

The mobile app must never include `CHARGER_EVENT_SECRET` and must never call `/charger-events/*`.

### Start session from charger event

```text
POST /charger-events/sessions/start
```

Request:

```json
{
  "reservation_id": "uuid",
  "started_at": "2026-05-23T19:10:25Z",
  "connector_type": "rapid",
  "charger_power_kw": 50.0
}
```

Validation/defaults:

```text
reservation_id: required
started_at: optional; defaults to now
connector_type: optional, max 100 chars
charger_power_kw: optional, >= 0
extra fields: forbidden
```

Response shape: `ChargingSessionRead`.

Backend behavior:

- Finds the reservation by ID.
- Rejects cancelled, expired, or completed reservations.
- Reconciles confirmed reservations past `reserved_until + 10 minutes` to `expired` and rejects start.
- Returns existing active session for the reservation if one already exists.
- Otherwise creates an active session and changes reservation status to `active`.

Failure cases:

```text
401 invalid charger event secret
404 invalid reservation ID / reservation not found
409 reservation cancelled
409 reservation expired
409 reservation already completed
```

### Complete session from charger event

```text
POST /charger-events/sessions/{session_id}/complete
```

Request:

```json
{
  "ended_at": "2026-05-23T19:40:25Z",
  "energy_kwh": 18.5,
  "cost_total": 7.4
}
```

Validation/defaults:

```text
ended_at: optional; defaults to now
energy_kwh: required, >= 0
cost_total: optional, >= 0
extra fields: forbidden
```

Backend behavior:

- Marks the session `completed`.
- Sets `ended_at`, `energy_kwh`, and `cost_total`.
- If linked to a reservation, marks that reservation `completed`.

Failure cases:

```text
401 invalid charger event secret
404 session not found
409 session already completed
```

---

## 12. Stations endpoints

These endpoints exist in backend. Normal mobile recommendation/reservation flow usually does not need to manage stations directly.

```text
GET    /stations
GET    /stations/{station_id}
POST   /stations
PUT    /stations/{station_id}
DELETE /stations/{station_id}
```

List filters:

```text
zone_id: optional
available_only: default false
public_only: default true
include_excluded: default false
```

Station write endpoints are not protected by auth in the uploaded code. Treat them as admin/demo/backoffice endpoints and protect/restrict before any public production deployment.

---

## 13. Lifecycle statuses

Reservation statuses:

```text
confirmed
active
completed
cancelled
expired
```

Charging session statuses:

```text
active
completed
stale_active
```

Mobile display rules:

```text
confirmed reservation without linked session -> Reserved Options
active session -> Active Charging
completed session -> Completed Charging
expired/cancelled reservation -> Attention Needed
stale_active session -> Attention Needed
```

---

## 14. Security rules

- JWT protects user endpoints.
- Refresh tokens are opaque and stored hashed server-side.
- Refresh token rotation happens on `/auth/refresh`.
- Logout revokes by refresh token and does not require a bearer token.
- Google login requires a valid Google ID token and configured Google web client ID.
- Password reset stores reset-token hashes only.
- Password reset should not return `development_reset_token` outside local/dev workflows.
- Charger-event secret protects internal charger/simulator endpoints.
- Mobile app must not include charger-event secret.
- Mobile app must not call `/charger-events/*`.
- Deployed production should replace all default secrets.
- Station write endpoints should be protected or removed from public exposure before production hardening.

Configuration values that must come from private deployment env, not Git:

```text
DATABASE_URL
JWT_SECRET_KEY
CHARGER_EVENT_SECRET
GOOGLE_WEB_CLIENT_ID
SMTP_HOST / SMTP credentials
SMTP_FROM_EMAIL
Android signing passwords / keystore
```

---

## 15. Error handling

Mobile should handle:

```text
400 bad request
401 unauthorized / token expired / invalid Google token
403 forbidden / inactive user
404 not found
409 lifecycle conflict / duplicate registration / runtime not started
422 validation error
500 backend error
```

Behavior:

- Show user-readable message.
- Do not expose stack traces.
- Do not retry non-idempotent POST requests automatically.
- For token expiry, try refresh once, then sign out if refresh fails.
- Do not reveal whether a password reset email belongs to an existing account.

---

## 16. Smoke-test expectation

A valid lifecycle smoke test should verify:

```text
register/login
refresh token
logout by refresh token
Google login when Google client ID is configured
password reset request creates email/link behavior
password reset confirm accepts link token and revokes old refresh tokens
GET /vehicles/me creates/returns vehicle profile
PUT /vehicles/me updates vehicle profile
mobile recommendation request validates target > current SOC
create reservation
charger event starts session
sessions/me shows active/completed state
charger event completes session
expired reservation blocks charger start
stale active session reconciles to stale_active
```

APK release smoke test should additionally verify:

```text
install ev-smart-charging-v0.1.6.apk
email/password sign up
email/password sign in
Continue with Google
request password reset
open reset-link email
set new password and sign in again
Profile -> Manage Vehicle
Profile -> App Settings
Profile -> Notifications
Profile -> Privacy & Security
Find Best Options
Reserve a charger
View Sessions
Log out
```
