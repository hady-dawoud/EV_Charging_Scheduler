# Mobile API Contract - EV Smart Charging App v0.1.6

**Last updated:** 2026-06-09  
**Latest tested APK baseline:** `ev-smart-charging-v0.1.6.apk`

## 1. Purpose

This document defines the API contract used by the production mobile app and the local web development harness.

The mobile app talks only to the FastAPI backend. It must not talk directly to PostgreSQL, Docker, the simulator runtime, or charger-event endpoints.

Production-style lifecycle:

```text
Mobile user creates reservation
Backend stores reservation
Charger/simulator/admin event starts session
Charger/simulator/admin event completes session
Mobile only displays reservation/session lifecycle state
```

v0.1.6 auth baseline:

- Email/password signup and login remain supported.
- Google sign-in and Google sign-up entry point are supported.
- Backend verifies Google ID tokens.
- Backend supports Google-linked user accounts.
- Password reset uses reset-link email flow, not manual token copy/paste.
- Reset Password screen handles the token internally when opened from the email link.

Contract-freeze note:

- This document was updated from the v0.1.6 release notes and previous handover/contract docs.
- Verify the exact Google auth route name and any extra Google response fields against `/api/openapi.json` or `apps/api` auth route code before final contract freeze.

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

Production/release builds must use the HTTPS API base. Do not ship Android builds pointing at the old insecure HTTP hosted URL.

---

## 3. Auth endpoints

Common token response shape:

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

- Save access token in memory.
- Save refresh token in secure storage.
- Native secure storage uses `react-native-keychain`.
- Web harness uses localStorage wrapper.
- For token expiry, try refresh once; if refresh fails, clear session and navigate to Login.

### Register with email/password

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

Response shape matches common token response.

Mobile behavior:

- Navigate to main app after success.
- Show validation errors from `422`.

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

Response shape matches common token response.

### Continue with Google

```text
POST /auth/google
```

Request:

```json
{
  "id_token": "google_id_token_from_google_sign_in",
  "device_id": "mobile-app"
}
```

Expected response shape matches common token response.

Backend behavior:

- Verify the Google ID token server-side.
- Create or link the user account using the verified Google identity.
- Issue normal app access/refresh tokens after successful verification.
- Do not trust client-provided Google profile fields without token verification.

Mobile behavior:

- Use Google sign-in to obtain the ID token.
- Send only the ID token and device identifier to the backend.
- Store the backend-issued access/refresh tokens like normal login.
- Do not treat Google client success as app login success until the backend returns app tokens.

Contract-freeze check:

- Confirm the exact endpoint path. If the backend uses a different route, update this section.

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

Response shape matches common token response.

### Logout

```text
POST /auth/logout
```

Request:

```json
{
  "refresh_token": "opaque_refresh_token",
  "device_id": "mobile-app"
}
```

Expected behavior:

- Revoke the refresh token.
- Do not require a bearer access token for logout.
- Return success for the active refresh-token logout path.

Mobile behavior:

- Call logout when possible.
- Clear local access token and refresh token whether logout succeeds or fails.
- Navigate to Login after clearing local session.

### Current user

```text
GET /auth/me
Authorization: Bearer <access_token>
```

Expected response:

```json
{
  "id": "uuid",
  "full_name": "Mobile User",
  "email": "mobile.user@example.com"
}
```

Mobile behavior:

- Use for session validation and profile identity display.
- Refresh once on `401`; if refresh fails, sign out.

---

## 4. Password reset

### Request password reset link

```text
POST /auth/password-reset/request
```

Request:

```json
{
  "email": "mobile.user@example.com"
}
```

Expected behavior:

- Create a short-lived hashed reset token record.
- Send a reset-link email using the configured Resend sender.
- The email link should open the Reset Password screen directly.
- The token should be handled internally by the app/web route.
- The endpoint should not reveal whether the email exists in a way that enables account enumeration.

Mobile/web behavior:

- Show a generic success message instructing the user to check email.
- Do not ask the user to manually copy/paste a reset token.
- If opened from the email link, hide the token field.

Email sender caveat:

- If using `onboarding@resend.dev`, describe delivery as development/testing only.
- Use a verified Resend sending domain before production-grade email claims.

### Confirm password reset

```text
POST /auth/password-reset/confirm
```

Request:

```json
{
  "token": "reset_token_from_email_link",
  "new_password": "newPassword123"
}
```

Expected behavior:

- Validate the reset token.
- Reject expired or already-used tokens.
- Update password hash.
- Mark reset token as used.
- Revoke active refresh tokens for that user.

Mobile behavior:

- When opened from email link, submit the internally captured token.
- After successful reset, navigate to Login.
- Ask the user to sign in with the new password.

---

## 5. Vehicle profile

### Get my vehicle profile

```text
GET /vehicles/me
Authorization: Bearer <access_token>
```

Expected response:

```json
{
  "make": "Tesla",
  "model": "Model 3",
  "battery_capacity_kwh": 75.0,
  "current_soc": 42,
  "range_km": 180
}
```

### Save my vehicle profile

```text
PUT /vehicles/me
Authorization: Bearer <access_token>
```

Request:

```json
{
  "make": "Tesla",
  "model": "Model 3",
  "battery_capacity_kwh": 75.0,
  "current_soc": 42,
  "range_km": 180
}
```

Expected response shape matches saved vehicle profile.

Field mapping:

```text
battery_capacity_kwh -> batteryCapacity
current_soc -> currentSoC
range_km -> rangeLeft
```

Mobile behavior:

- Profile → Manage Vehicle reads and writes this backend profile.
- Home battery display should reflect saved `current_soc`.
- Charging Request should use saved `current_soc` and `battery_capacity_kwh`.
- Do not use hardcoded `mockVehicle` values when saved vehicle data exists.

---

## 6. System endpoint

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

- Use for backend/runtime availability checks.
- Do not crash if unavailable.
- Do not retry aggressively.

---

## 7. Recommendations

### Mobile recommendations

```text
POST /mobile/recommendations
Authorization: Bearer <access_token>
```

Request:

```json
{
  "target_soc": 80,
  "preference_mode": "cheapest",
  "charger_type": "any"
}
```

Accepted values:

```text
preference_mode: cheapest | fastest | closest
charger_type: any | ac | dc
```

Vehicle data behavior:

- Backend/mobile recommendation input should use the saved vehicle profile where applicable.
- Current charge and battery capacity should come from saved vehicle data, not mock state.

Response:

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

- Use `top_recommendation` as primary recommendation.
- Use `alternatives` as alternative cards.
- Preserve `request_id`, `client_request_id`, selected `station_id`, and selected rank for reservation.
- Do not calculate recommendations locally.
- Do not automatically retry this POST request because duplicate live requests can pollute the simulator runtime.

---

## 8. Reservations

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

Response:

```json
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
```

Mobile behavior:

- Show confirmation screen after success.
- Store no local-only reservation state.
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
- Confirmed reservations past `reserved_until + grace period` become `expired`.

### Cancel reservation

```text
PATCH /reservations/{reservation_id}/cancel
Authorization: Bearer <access_token>
```

Mobile behavior:

- Use only if cancellation UI is added.
- Cancelled reservations should no longer appear as waiting reservations.

---

## 9. Charging sessions

Mobile can only read charging sessions.

Mobile must not start or complete sessions directly.

### List my charging sessions

```text
GET /sessions/me
Authorization: Bearer <access_token>
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

- Reconciles stale active sessions.
- Active sessions older than estimated duration plus grace become `stale_active`.
- If no estimate exists, default stale threshold applies.

### Get active charging session

```text
GET /sessions/active
Authorization: Bearer <access_token>
```

Response:

```json
{
  "session": null
}
```

or:

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

---

## 10. Internal charger-event endpoints

These endpoints are not for the mobile app UI.

They represent charger/provider/simulator/admin events.

Authentication:

```text
X-Charger-Event-Secret: <internal-secret>
```

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

Response:

```json
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
```

Failure cases:

```text
401 invalid charger event secret
404 reservation not found
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

Failure cases:

```text
401 invalid charger event secret
404 session not found
409 session already completed
```

---

## 11. Lifecycle statuses

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

## 12. Security rules

- JWT protects user endpoints.
- Refresh tokens are opaque and stored securely.
- Google ID tokens must be verified by the backend before creating/linking app accounts.
- Password reset tokens are short-lived and one-time use.
- Charger-event secret protects internal charger/simulator endpoints.
- Mobile app must not include charger-event secret.
- Mobile app must not call `/charger-events/*`.
- Deployed production should replace all default secrets.
- Android signing key and passwords must stay outside Git.
- Resend API key and sending-domain configuration must stay outside Git.

---

## 13. Error handling

Mobile should handle:

```text
400 bad request
401 unauthorized / token expired
403 forbidden
404 not found
409 lifecycle conflict
422 validation error
500 backend error
```

Behavior:

- Show user-readable message.
- Do not expose stack traces.
- Do not retry non-idempotent POST requests automatically.
- For token expiry, try refresh once, then sign out if refresh fails.
- For Google auth failure, show a generic sign-in failure and allow email/password fallback.
- For password reset request, avoid account-existence wording.

---

## 14. Smoke-test expectation

A valid local lifecycle smoke test should verify:

```text
register/login
Google sign-in backend token exchange where available
request password reset email
open reset-link and set new password
create/update vehicle profile
create recommendation request using saved vehicle data
create reservation
charger event starts session
sessions/me shows active/completed state
charger event completes session
expired reservation blocks charger start
stale active session reconciles to stale_active
logout revokes refresh token without requiring bearer token
```

---

## 15. v0.1.6 APK post-install checklist

```text
Sign in with email/password
Sign up with email/password
Continue with Google
Request password reset
Open the reset-link email
Set a new password and sign in again
Profile -> Manage Vehicle
Profile -> App Settings
Profile -> Notifications
Profile -> Privacy & Security
Find Best Options
Reserve a charger
View Sessions
Log out
```

---

## 16. Open contract items to verify from code/OpenAPI

The following should be checked against `/api/openapi.json` or the `apps/api` route files before final contract freeze:

- Exact Google auth endpoint path. This document records it as `POST /auth/google` based on common backend naming and v0.1.6 release notes.
- Exact Google auth request field names if the backend uses `idToken`, `credential`, or another field instead of `id_token`.
- Whether user response includes provider/auth metadata such as `auth_provider`, `google_sub`, or `is_google_linked`.
- Whether password reset request returns only a generic message or also additional development-only fields in non-production mode.
- Whether `GET /auth/me` includes extra profile fields.
