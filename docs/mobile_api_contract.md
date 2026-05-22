# Mobile API Contract — EV Smart Charging App

## 1. Purpose

This document defines the backend API contract used by the production Android mobile app.

Mobile stack:

- React Native CLI
- TypeScript
- React Navigation
- TanStack Query
- Zustand
- React Native Maps
- react-native-keychain
- Signed Android release APK

Backend stack:

- FastAPI
- PostgreSQL
- JWT access token + refresh token
- EV simulator runtime / recommender integration

Rule:

The mobile app talks only to the FastAPI backend. It must not connect directly to PostgreSQL and must not call the simulator runtime directly.

---

## 2. Base URLs

### Android emulator

```text
http://10.0.2.2:8000
```

### Physical Android phone on same network

```text
http://<your-computer-lan-ip>:8000
```

### Deployed backend

```text
http://smartevcharging.uaenorth.cloudapp.azure.com/api
```

The deployed backend uses the `/api` reverse-proxy prefix.

In local FastAPI/TestClient tests, routes are called without `/api`.

---

## 3. Implemented mobile backend endpoints

### Auth

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

### Stations

```text
GET    /stations
GET    /stations/{station_id}
POST   /stations
PUT    /stations/{station_id}
DELETE /stations/{station_id}
```

### Recommendations

```text
POST /recommendations
POST /mobile/recommendations
```

### Reservations

```text
POST  /reservations
GET   /reservations/me
PATCH /reservations/{reservation_id}/cancel
```

### Charging sessions

```text
POST  /sessions
GET   /sessions/me
GET   /sessions/active
PATCH /sessions/{session_id}/complete
```

---

## 4. Auth contract

Auth uses JWT access tokens and persisted refresh tokens.

Mobile storage rules:

- Store refresh token in `react-native-keychain`.
- Keep access token in memory through Zustand.
- Do not store tokens in AsyncStorage.
- Do not persist access token in plain local storage.
- Clear tokens on logout or failed refresh.

---

### 4.1 Register

```text
POST /auth/register
```

Request:

```json
{
  "full_name": "Alex Mercer",
  "email": "alex.mercer@example.com",
  "password": "password123"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "full_name": "Alex Mercer",
    "email": "alex.mercer@example.com"
  },
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "bearer"
}
```

Expected statuses:

```text
201 Created
409 Email already registered
422 Validation error
```

---

### 4.2 Login

```text
POST /auth/login
```

Request:

```json
{
  "email": "alex.mercer@example.com",
  "password": "password123",
  "device_id": "android-device-id"
}
```

Response:

```json
{
  "user": {
    "id": "uuid",
    "full_name": "Alex Mercer",
    "email": "alex.mercer@example.com"
  },
  "access_token": "jwt_access_token",
  "refresh_token": "jwt_refresh_token",
  "token_type": "bearer"
}
```

Expected statuses:

```text
200 OK
401 Invalid email or password
403 Inactive user
422 Validation error
```

---

### 4.3 Refresh token

```text
POST /auth/refresh
```

Request:

```json
{
  "refresh_token": "jwt_refresh_token",
  "device_id": "android-device-id"
}
```

Response:

```json
{
  "access_token": "new_jwt_access_token",
  "refresh_token": "new_jwt_refresh_token",
  "token_type": "bearer"
}
```

Backend behavior:

- Refresh tokens are rotated.
- Old refresh token is revoked after refresh.
- Refresh tokens are stored hashed in PostgreSQL.

Mobile behavior:

- Call during app startup.
- Call once after a `401`.
- Retry the original request once after successful refresh.
- If refresh fails, clear auth state and route to Login.

---

### 4.4 Current user

```text
GET /auth/me
```

Headers:

```text
Authorization: Bearer <access_token>
```

Response:

```json
{
  "id": "uuid",
  "full_name": "Alex Mercer",
  "email": "alex.mercer@example.com"
}
```

Expected statuses:

```text
200 OK
401 Missing or invalid bearer token
403 Inactive user
```

---

### 4.5 Logout

```text
POST /auth/logout
```

Headers:

```text
Authorization: Bearer <access_token>
```

Request:

```json
{
  "refresh_token": "jwt_refresh_token"
}
```

Response:

```json
{
  "success": true
}
```

Mobile behavior:

- Revoke refresh token on backend.
- Clear Keychain.
- Clear Zustand auth state.
- Clear TanStack Query cache.
- Route to Login/Splash.

---

## 5. Stations contract

Stations are persisted in PostgreSQL.

Important:

- Station IDs are strings.
- Do not use numeric station IDs.
- `station_id` values match recommender output.

Example station IDs:

```text
greenmarket_150kw_bus_charger
princes_street_charging_hub_dundee
clepington_road_4th_hub
```

---

### 5.1 List stations

```text
GET /stations
```

Query params:

```text
zone_id?: string
available_only?: boolean
public_only?: boolean
include_excluded?: boolean
```

Example:

```text
GET /stations?available_only=true&public_only=true
```

Response:

```json
{
  "stations": [
    {
      "station_id": "greenmarket_150kw_bus_charger",
      "station_name": "Greenmarket 150kW Bus Charger",
      "postcode": null,
      "latitude": 56.462,
      "longitude": -2.9707,
      "zone_id": "zone_central_waterfront",
      "transformer_id": "tx_central_market",
      "cp_count_total": 1,
      "connector_mix_total": "ultra_rapid",
      "station_max_power_kw_proxy": 150.0,
      "station_capacity_kw_assumed": 260.0,
      "is_public": true,
      "is_fleet_only": false,
      "requires_membership": false,
      "exclude_from_recommendations": false,
      "access_notes": null,
      "location_source": "osm_road_match",
      "location_confidence": "medium",
      "needs_followup": false,
      "sessions_total": 100,
      "energy_total_kwh": 5000.0
    }
  ]
}
```

Mobile usage:

- Map pins.
- Station list.
- Station details.
- Recommendation fallback lookup.

---

### 5.2 Get station by ID

```text
GET /stations/{station_id}
```

Example:

```text
GET /stations/greenmarket_150kw_bus_charger
```

Expected statuses:

```text
200 OK
404 Station not found
```

---

## 6. Recommendation contract

There are two recommendation endpoints:

```text
POST /recommendations
POST /mobile/recommendations
```

Use `/mobile/recommendations` in the React Native app.

Keep `/recommendations` as the raw runtime contract endpoint.

---

### 6.1 Mobile recommendation endpoint

```text
POST /mobile/recommendations
```

Headers:

```text
Authorization: Bearer <access_token>
```

Purpose:

Accept a mobile-friendly charging request, translate it to the simulator runtime contract, and return ranked station recommendations.

Request:

```json
{
  "client_request_id": "optional-client-request-id",
  "latitude": 56.462,
  "longitude": -2.970,
  "battery_level": 35,
  "target_battery_level": 80,
  "battery_kwh": 60,
  "vehicle_profile_id": null,
  "vehicle_max_ac_kw": 11,
  "vehicle_max_dc_kw": 150,
  "requested_energy_kwh": null,
  "preference_mode": "fastest",
  "connector_type": "rapid",
  "latest_finish_minutes_from_now": 90,
  "zone_id": null,
  "metadata": {
    "source_screen": "recommendation_form"
  }
}
```

Fields:

```text
client_request_id optional
latitude optional
longitude optional
battery_level optional, 0..100
target_battery_level optional, 0..100
battery_kwh optional, default 60
vehicle_max_ac_kw optional, default 11
vehicle_max_dc_kw optional, default 150
requested_energy_kwh optional
preference_mode closest | cheapest | fastest
connector_type string, default Any
latest_finish_minutes_from_now default 90
zone_id optional
metadata optional object
```

Backend behavior:

- Requires JWT auth.
- Generates `client_request_id` if missing.
- Generates `request_timestamp`.
- Generates `latest_finish_ts`.
- Injects authenticated user ID into metadata.
- Calls simulator runtime.
- Returns runtime `RecommendationResponse`.

Response:

```json
{
  "request_id": "external_abc123",
  "client_request_id": "mobile_uuid_suffix",
  "simulated_timestamp": "2024-06-21T11:30:00",
  "zone_id": "zone_central_waterfront",
  "top_recommendation": {
    "station_id": "princes_street_charging_hub_dundee",
    "station_name": "Princes Street Charging Hub, Dundee",
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
    "reason_tags": [
      "nearby",
      "low_wait",
      "high_headroom",
      "charger_match"
    ],
    "metadata": {
      "connector_mix_total": "ac;rapid",
      "selected_connector_type": "rapid",
      "selected_connector_power_kw": 50.0,
      "selected_connector_id": "APT51425",
      "effective_power_kw": 50.0,
      "price_per_kwh": 0.6417
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

- Use `top_recommendation` as primary card.
- Use `alternatives` as alternative cards.
- Store `request_id`, `client_request_id`, selected `station_id`, and selected rank for reservation.
- Do not calculate recommendations locally.
- Do not automatically retry this POST request.

Important retry rule:

Do not automatically retry recommendation POST requests because they inject live requests into the simulator runtime.

Expected statuses:

```text
200 OK
401 Missing or invalid access token
409 Runtime not started
422 Validation error
500 Backend error
```

---

### 6.2 Raw runtime recommendation endpoint

```text
POST /recommendations
```

Purpose:

Raw simulator integration endpoint. Not recommended for the mobile app UI.

Request source of truth:

```text
ExternalChargingRequest
```

Required fields:

```text
client_request_id
request_timestamp
latest_finish_ts
```

Useful optional fields:

```text
current_latitude
current_longitude
target_soc
current_soc
battery_kwh
vehicle_profile_id
vehicle_max_ac_kw
vehicle_max_dc_kw
requested_energy_kwh
preference_mode
charger_type
source_type
request_id
zone_id
metadata
```

Valid preference modes:

```text
closest
cheapest
fastest
```

Response source of truth:

```text
RecommendationResponse
```

---

## 7. Reservations contract

Reservations are authenticated and persisted in PostgreSQL.

---

### 7.1 Create reservation

```text
POST /reservations
```

Headers:

```text
Authorization: Bearer <access_token>
```

Request:

```json
{
  "client_request_id": "mobile-client-request-id",
  "request_id": "runtime-request-id",
  "station_id": "greenmarket_150kw_bus_charger",
  "recommendation_rank": 1,
  "reserved_start_at": "2026-06-01T10:00:00Z",
  "reserved_until": null
}
```

Rules:

- `station_id` must exist in PostgreSQL.
- `reserved_until` is optional.
- If `reserved_until` is missing, backend defaults to 15 minutes after `reserved_start_at`.

Response:

```json
{
  "reservation_id": "uuid",
  "status": "confirmed",
  "station_id": "greenmarket_150kw_bus_charger",
  "station_name": "Greenmarket 150kW Bus Charger",
  "client_request_id": "mobile-client-request-id",
  "request_id": "runtime-request-id",
  "recommendation_rank": 1,
  "reserved_start_at": "2026-06-01T10:00:00Z",
  "reserved_until": "2026-06-01T10:15:00Z",
  "cancelled_at": null,
  "created_at": "2026-05-22T12:00:00Z"
}
```

Expected statuses:

```text
201 Created
401 Unauthorized
404 Station not found
422 Validation error
```

---

### 7.2 List my reservations

```text
GET /reservations/me
```

Headers:

```text
Authorization: Bearer <access_token>
```

Response:

```json
{
  "reservations": [
    {
      "reservation_id": "uuid",
      "status": "confirmed",
      "station_id": "greenmarket_150kw_bus_charger",
      "station_name": "Greenmarket 150kW Bus Charger",
      "client_request_id": "mobile-client-request-id",
      "request_id": "runtime-request-id",
      "recommendation_rank": 1,
      "reserved_start_at": "2026-06-01T10:00:00Z",
      "reserved_until": "2026-06-01T10:15:00Z",
      "cancelled_at": null,
      "created_at": "2026-05-22T12:00:00Z"
    }
  ]
}
```

Expected statuses:

```text
200 OK
401 Unauthorized
```

---

### 7.3 Cancel reservation

```text
PATCH /reservations/{reservation_id}/cancel
```

Headers:

```text
Authorization: Bearer <access_token>
```

Response:

```json
{
  "reservation_id": "uuid",
  "status": "cancelled"
}
```

Expected statuses:

```text
200 OK
401 Unauthorized
404 Reservation not found
409 Already cancelled
```

---

## 8. Charging sessions contract

Charging sessions are authenticated and persisted in PostgreSQL.

---

### 8.1 Start session

```text
POST /sessions
```

Headers:

```text
Authorization: Bearer <access_token>
```

Request:

```json
{
  "station_id": "greenmarket_150kw_bus_charger",
  "reservation_id": "optional-reservation-uuid",
  "client_request_id": "mobile-client-request-id",
  "request_id": "runtime-request-id",
  "started_at": "2026-06-01T10:00:00Z",
  "connector_type": "rapid",
  "charger_power_kw": 150
}
```

Rules:

- `station_id` must exist.
- `reservation_id` is optional.
- If `reservation_id` is provided, it must belong to the authenticated user.
- If `started_at` is missing, backend uses current server time.

Response:

```json
{
  "session_id": "uuid",
  "status": "active",
  "station_id": "greenmarket_150kw_bus_charger",
  "station_name": "Greenmarket 150kW Bus Charger",
  "reservation_id": "optional-reservation-uuid",
  "client_request_id": "mobile-client-request-id",
  "request_id": "runtime-request-id",
  "started_at": "2026-06-01T10:00:00Z",
  "ended_at": null,
  "energy_kwh": 0,
  "cost_total": null,
  "connector_type": "rapid",
  "charger_power_kw": 150,
  "created_at": "2026-05-22T12:00:00Z"
}
```

Expected statuses:

```text
201 Created
401 Unauthorized
404 Station or reservation not found
422 Validation error
```

---

### 8.2 Get active session

```text
GET /sessions/active
```

Headers:

```text
Authorization: Bearer <access_token>
```

Response when active:

```json
{
  "session": {
    "session_id": "uuid",
    "status": "active",
    "station_id": "greenmarket_150kw_bus_charger",
    "station_name": "Greenmarket 150kW Bus Charger",
    "reservation_id": "optional-reservation-uuid",
    "client_request_id": "mobile-client-request-id",
    "request_id": "runtime-request-id",
    "started_at": "2026-06-01T10:00:00Z",
    "ended_at": null,
    "energy_kwh": 0,
    "cost_total": null,
    "connector_type": "rapid",
    "charger_power_kw": 150,
    "created_at": "2026-05-22T12:00:00Z"
  }
}
```

Response when none:

```json
{
  "session": null
}
```

---

### 8.3 List my sessions

```text
GET /sessions/me
```

Optional query:

```text
status=active
status=completed
```

Headers:

```text
Authorization: Bearer <access_token>
```

Response:

```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "status": "completed",
      "station_id": "greenmarket_150kw_bus_charger",
      "station_name": "Greenmarket 150kW Bus Charger",
      "reservation_id": "optional-reservation-uuid",
      "client_request_id": "mobile-client-request-id",
      "request_id": "runtime-request-id",
      "started_at": "2026-06-01T10:00:00Z",
      "ended_at": "2026-06-01T10:30:00Z",
      "energy_kwh": 18.5,
      "cost_total": 9.25,
      "connector_type": "rapid",
      "charger_power_kw": 150,
      "created_at": "2026-05-22T12:00:00Z"
    }
  ]
}
```

---

### 8.4 Complete session

```text
PATCH /sessions/{session_id}/complete
```

Headers:

```text
Authorization: Bearer <access_token>
```

Request:

```json
{
  "ended_at": "2026-06-01T10:30:00Z",
  "energy_kwh": 18.5,
  "cost_total": 9.25
}
```

Response:

```json
{
  "session_id": "uuid",
  "status": "completed",
  "station_id": "greenmarket_150kw_bus_charger",
  "station_name": "Greenmarket 150kW Bus Charger",
  "reservation_id": "optional-reservation-uuid",
  "client_request_id": "mobile-client-request-id",
  "request_id": "runtime-request-id",
  "started_at": "2026-06-01T10:00:00Z",
  "ended_at": "2026-06-01T10:30:00Z",
  "energy_kwh": 18.5,
  "cost_total": 9.25,
  "connector_type": "rapid",
  "charger_power_kw": 150,
  "created_at": "2026-05-22T12:00:00Z"
}
```

Expected statuses:

```text
200 OK
401 Unauthorized
404 Session not found
409 Already completed
422 Validation error
```

---

## 9. Standard error handling

### 9.1 Validation error

```text
422
```

Use field-level errors where possible.

Common causes:

- Invalid email
- Short password
- Invalid SOC range
- Missing station ID
- Bad UUID
- Invalid date-time
- Unknown extra fields

---

### 9.2 Unauthorized

```text
401
```

Mobile behavior:

- Try refresh token once.
- Retry original request once if refresh succeeds.
- If refresh fails, clear Keychain and route to Login.

---

### 9.3 Forbidden

```text
403
```

Used for inactive users.

---

### 9.4 Not found

```text
404
```

Used for missing station, reservation, or session.

---

### 9.5 Conflict

```text
409
```

Used for:

- Duplicate registration email
- Duplicate station create
- Already-cancelled reservation
- Already-completed session
- Runtime unavailable

---

### 9.6 Server error

```text
500
```

Mobile behavior:

Show generic backend error. Do not expose internal stack traces.

---

## 10. Mobile implementation rules

### 10.1 TanStack Query server state

Use TanStack Query for:

- auth profile
- stations
- station details
- recommendations
- reservations
- sessions

Recommended mutation retry policy:

- Auth mutations: no automatic retries.
- Recommendation mutations: no automatic retries.
- Reservation mutations: no automatic retries unless user explicitly taps again.
- Session mutations: no automatic retries unless idempotency is added later.
- GET queries may retry carefully.

---

### 10.2 Zustand app state

Use Zustand for:

- auth status
- in-memory access token
- selected recommendation
- charging request draft
- active map filters
- UI/demo preferences

Do not use Zustand as the only source of truth for:

- reservations
- sessions
- station catalog
- auth refresh token

---

### 10.3 Secure storage

Use `react-native-keychain` for:

- refresh token

Do not store tokens in:

- AsyncStorage
- source code
- committed env files
- plain Zustand persistence

---

## 11. End-to-end mobile flow

### 11.1 Startup

```text
Read refresh token from Keychain
POST /auth/refresh
GET /auth/me
Load authenticated app
```

If refresh fails:

```text
Clear Keychain
Clear auth state
Show Login
```

---

### 11.2 Main recommendation flow

```text
POST /mobile/recommendations
Display top_recommendation + alternatives
User selects recommendation
POST /reservations
Show reservation confirmation
POST /sessions when charging starts
PATCH /sessions/{session_id}/complete when charging ends
```

Important:

Save these fields from the selected recommendation:

```text
request_id
client_request_id
station_id
recommendation_rank
station_name
estimated_cost_gbp
estimated_duration_minutes
selected_connector_type from metadata when available
selected_connector_power_kw from metadata when available
```

---

## 12. Backend implementation status

Implemented:

```text
JWT auth
refresh token persistence and revocation
PostgreSQL users
PostgreSQL stations
station seed script
mobile recommendation wrapper
raw runtime recommendation endpoint
authenticated reservations
authenticated charging sessions
```

Still optional/future:

```text
charging_requests persistence
recommendation_results persistence
vehicle profiles
payment records
admin-only station mutation protection
role-based access control
idempotency keys for mutations
```

---

## 13. Final contract principle

The mobile app is a user-facing product.

It should:

- send authenticated charging requests
- display backend-generated recommendations
- reserve selected station options
- show active and past sessions
- manage profile/auth state
- use PostgreSQL-backed backend state

It should not:

- expose simulator internals directly
- calculate recommendations locally
- connect directly to PostgreSQL
- store important state only in memory
- treat runtime/dashboard as part of the user app
