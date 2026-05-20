# Mobile API Contract - EV Smart Charging App

## 1. Purpose

This document defines the API contract used by the production Android mobile app.

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
- Existing EV simulator runtime / recommender integration

Rule:
The mobile app talks only to the FastAPI backend. It must not talk directly to PostgreSQL or directly to the simulator runtime.

---

## 2. Base URLs

Local Android emulator:

    http://10.0.2.2:8000

Local physical Android phone:

    http://<your-computer-lan-ip>:8000

Deployed backend:

    http://smartevcharging.uaenorth.cloudapp.azure.com/api

The deployed backend uses the /api reverse-proxy prefix.

---

## 3. Endpoint status legend

EXISTS_NOW:
Endpoint already exists.

NEEDS_BUILD:
Endpoint must be implemented.

NEEDS_DB:
Endpoint needs PostgreSQL persistence.

---

## 4. Existing system endpoints

### 4.1 Health check

Endpoint:

    GET /health

Status:

    EXISTS_NOW

Purpose:
Used by the mobile app to check backend and runtime availability.

Expected response shape:

    {
      "status": "ok",
      "runtime_started": true,
      "loop_running": true,
      "runtime_mode": "hybrid",
      "active_policy": "overload_aware",
      "simulated_timestamp": "2024-06-10T14:30:00"
    }

Mobile behavior:
- If the backend is unreachable, show backend unavailable.
- If runtime_started is false, show recommendation runtime unavailable.
- Do not crash.
- Do not keep retrying aggressively.

---

### 4.2 Runtime status

Endpoint:

    GET /runtime/status

Status:

    EXISTS_NOW

Purpose:
Optional app/debug status display.

Mobile behavior:
- Not required for normal user flow.
- Useful for a hidden debug/status screen.

---

### 4.3 Runtime state

Endpoint:

    GET /runtime/state

Status:

    EXISTS_NOW

Mobile behavior:
- Optional.
- Do not expose simulator internals in normal user UI.

---

### 4.4 Runtime events

Endpoint:

    GET /runtime/events?limit=50

Status:

    EXISTS_NOW

Mobile behavior:
- Optional debug/admin usage only.

---

### 4.5 Recent runtime recommendations

Endpoint:

    GET /runtime/recommendations/recent?limit=20

Status:

    EXISTS_NOW

Mobile behavior:
- Optional debug/admin usage only.

---

## 5. Auth endpoints

These do not exist yet.

### 5.1 Register

Endpoint:

    POST /auth/register

Status:

    NEEDS_BUILD
    NEEDS_DB

Request:

    {
      "full_name": "Alex Mercer",
      "email": "alex.mercer@example.com",
      "password": "password123"
    }

Response:

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

Rules:
- Email must be unique.
- Password must be hashed.
- Raw password must never be stored.
- Raw password must never be returned.

---

### 5.2 Login

Endpoint:

    POST /auth/login

Status:

    NEEDS_BUILD
    NEEDS_DB

Request:

    {
      "email": "alex.mercer@example.com",
      "password": "password123"
    }

Response:

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

Mobile behavior:
- Store refresh token using react-native-keychain.
- Keep access token in memory.
- Navigate to authenticated app stack.

---

### 5.3 Refresh token

Endpoint:

    POST /auth/refresh

Status:

    NEEDS_BUILD
    NEEDS_DB

Request:

    {
      "refresh_token": "jwt_refresh_token"
    }

Response:

    {
      "access_token": "new_jwt_access_token",
      "refresh_token": "new_or_existing_refresh_token",
      "token_type": "bearer"
    }

Mobile behavior:
- Called on app startup from Splash.
- Called once after receiving 401.
- If refresh fails, clear Keychain and route to Login.

---

### 5.4 Current user

Endpoint:

    GET /auth/me

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Response:

    {
      "id": "uuid",
      "full_name": "Alex Mercer",
      "email": "alex.mercer@example.com"
    }

---

### 5.5 Logout

Endpoint:

    POST /auth/logout

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Request:

    {
      "refresh_token": "jwt_refresh_token"
    }

Response:

    {
      "success": true
    }

Mobile behavior:
- Revoke refresh token on backend.
- Clear Keychain.
- Clear Zustand auth state.
- Clear TanStack Query cache.
- Route to Login/Splash.

---

## 6. Station endpoints

### 6.1 List stations

Endpoint:

    GET /stations

Status:

    EXISTS_NOW
    NEEDS_DB

Current limitation:
The current backend station service uses in-memory mock station data.

Target response:

    {
      "stations": [
        {
          "station_id": "greenmarket_150kw_bus_charger",
          "station_name": "Greenmarket 150kW Bus Charger",
          "latitude": 56.462,
          "longitude": -2.9707,
          "zone_id": "zone_central_waterfront",
          "transformer_id": "tx_central_market",
          "available_ports": 3,
          "cp_count_total": 4,
          "connector_mix_total": "ultra_rapid",
          "station_capacity_kw_assumed": 150.0,
          "price_per_kwh": 0.32,
          "status": "open"
        }
      ]
    }

Mobile usage:
- Station map pins.
- Station list.
- Station details.
- Recommendation fallback lookup.

---

### 6.2 Get station by ID

Endpoint:

    GET /stations/{station_id}

Status:

    EXISTS_NOW
    NEEDS_DB

Target response:

    {
      "station_id": "greenmarket_150kw_bus_charger",
      "station_name": "Greenmarket 150kW Bus Charger",
      "latitude": 56.462,
      "longitude": -2.9707,
      "zone_id": "zone_central_waterfront",
      "transformer_id": "tx_central_market",
      "available_ports": 3,
      "cp_count_total": 4,
      "connector_mix_total": "ultra_rapid",
      "station_capacity_kw_assumed": 150.0,
      "price_per_kwh": 0.32,
      "status": "open"
    }

---

## 7. Recommendation endpoint

### 7.1 Create recommendation request

Endpoint:

    POST /recommendations

Status:

    EXISTS_NOW

Purpose:
The mobile app sends a charging request. The backend injects it into the EV simulator runtime and returns ranked station recommendations.

Do not calculate recommendations in the mobile app.

Request source of truth:

    ExternalChargingRequest

Required request fields:
- client_request_id
- request_timestamp
- latest_finish_ts
- preference_mode
- charger_type
- source_type

Recommended mobile request fields:
- current_latitude
- current_longitude
- target_soc
- current_soc
- battery_kwh
- requested_energy_kwh
- zone_id
- metadata.channel

Request example:

    {
      "client_request_id": "mobile-1710000000000",
      "request_timestamp": "2026-05-20T14:00:00Z",
      "current_latitude": 56.462,
      "current_longitude": -2.9707,
      "target_soc": 80,
      "current_soc": 45,
      "battery_kwh": 82,
      "vehicle_profile_id": null,
      "vehicle_max_ac_kw": null,
      "vehicle_max_dc_kw": null,
      "requested_energy_kwh": 28.7,
      "preference_mode": "cheapest",
      "charger_type": "Any",
      "latest_finish_ts": "2026-05-20T16:00:00Z",
      "source_type": "external_live",
      "request_id": "mobile-live-1710000000000",
      "zone_id": "zone_central_waterfront",
      "metadata": {
        "channel": "mobile-app"
      }
    }

Valid preference_mode values:
- closest
- cheapest
- fastest

Valid source_type values:
- replay_background
- synthetic_background
- external_live

Valid charger_type values:
- Any
- AC
- DC
- Rapid
- UltraRapid
- ultra_rapid

Response source of truth:

    RecommendationResponse

Response example:

    {
      "request_id": "runtime-request-id",
      "client_request_id": "mobile-1710000000000",
      "simulated_timestamp": "2024-06-10T14:30:00",
      "zone_id": "zone_central_waterfront",
      "top_recommendation": {
        "station_id": "greenmarket_150kw_bus_charger",
        "station_name": "Greenmarket 150kW Bus Charger",
        "zone_id": "zone_central_waterfront",
        "transformer_id": "tx_central_market",
        "score": 0.7521,
        "distance_km": 0.502,
        "estimated_wait_minutes": 0,
        "estimated_duration_minutes": 15,
        "estimated_cost_gbp": 4.86,
        "transformer_headroom_kw": 379.073,
        "current_queue": 0,
        "utilization": 0.0,
        "charger_compatible": true,
        "reason_tags": [
          "nearby",
          "low_wait",
          "high_headroom",
          "low_cost"
        ],
        "metadata": {
          "connector_mix_total": "ultra_rapid"
        }
      },
      "alternatives": [],
      "congestion_note": null,
      "debug_reasoning_summary": "",
      "source_type": "external_live",
      "metadata": {}
    }

Mobile behavior:
- Call POST /recommendations only once per user request.
- Do not automatically retry POST /recommendations.
- Preserve client_request_id.
- On 409, show runtime unavailable.
- On 422, show validation error.
- On 500, show backend error.

Important:
POST /recommendations should not be automatically retried because retrying can inject duplicate live requests into the simulator runtime.

---

## 8. Reservation endpoints

These do not exist yet.

### 8.1 Create reservation

Endpoint:

    POST /reservations

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Request:

    {
      "client_request_id": "mobile-1710000000000",
      "request_id": "runtime-request-id",
      "station_id": "greenmarket_150kw_bus_charger",
      "recommendation_rank": 1,
      "reserved_start_at": "2026-05-20T14:30:00Z"
    }

Response:

    {
      "reservation_id": "uuid",
      "status": "confirmed",
      "station_id": "greenmarket_150kw_bus_charger",
      "station_name": "Greenmarket 150kW Bus Charger",
      "reserved_start_at": "2026-05-20T14:30:00Z",
      "reserved_until": "2026-05-20T14:45:00Z",
      "created_at": "2026-05-20T14:02:00Z"
    }

Mobile behavior:
- Create reservation only after user selects a recommendation.
- Show confirmation only after backend confirms.
- Do not use in-memory-only reservation state.

---

### 8.2 List my reservations

Endpoint:

    GET /reservations/me

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Response:

    {
      "reservations": [
        {
          "reservation_id": "uuid",
          "status": "confirmed",
          "station_id": "greenmarket_150kw_bus_charger",
          "station_name": "Greenmarket 150kW Bus Charger",
          "reserved_start_at": "2026-05-20T14:30:00Z",
          "reserved_until": "2026-05-20T14:45:00Z"
        }
      ]
    }

---

### 8.3 Cancel reservation

Endpoint:

    PATCH /reservations/{reservation_id}/cancel

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Response:

    {
      "reservation_id": "uuid",
      "status": "cancelled"
    }

---

## 9. Charging session endpoints

These do not exist yet.

### 9.1 Start session

Endpoint:

    POST /sessions/start

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Request:

    {
      "reservation_id": "uuid"
    }

Response:

    {
      "session_id": "uuid",
      "reservation_id": "uuid",
      "station_id": "greenmarket_150kw_bus_charger",
      "status": "active",
      "started_at": "2026-05-20T14:30:00Z"
    }

---

### 9.2 Get active session

Endpoint:

    GET /sessions/active

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Response when active:

    {
      "session_id": "uuid",
      "reservation_id": "uuid",
      "station_id": "greenmarket_150kw_bus_charger",
      "station_name": "Greenmarket 150kW Bus Charger",
      "status": "active",
      "started_at": "2026-05-20T14:30:00Z",
      "estimated_end_at": "2026-05-20T14:45:00Z"
    }

Response when no active session:

    {
      "session": null
    }

---

### 9.3 End session

Endpoint:

    POST /sessions/{session_id}/end

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Response:

    {
      "session_id": "uuid",
      "status": "completed",
      "started_at": "2026-05-20T14:30:00Z",
      "ended_at": "2026-05-20T14:47:00Z",
      "energy_kwh": 28.7,
      "cost_gbp": 4.86
    }

---

### 9.4 List my sessions

Endpoint:

    GET /sessions/me

Status:

    NEEDS_BUILD
    NEEDS_DB

Headers:

    Authorization: Bearer <access_token>

Response:

    {
      "sessions": [
        {
          "session_id": "uuid",
          "station_id": "greenmarket_150kw_bus_charger",
          "station_name": "Greenmarket 150kW Bus Charger",
          "status": "completed",
          "started_at": "2026-05-20T14:30:00Z",
          "ended_at": "2026-05-20T14:47:00Z",
          "energy_kwh": 28.7,
          "cost_gbp": 4.86
        }
      ]
    }

---

## 10. Standard error handling

### 10.1 Validation error

HTTP status:

    422

Mobile behavior:
Show field-level validation message where possible.

Common causes:
- invalid SOC range
- target SOC lower than current SOC
- invalid charger type
- invalid latitude/longitude
- latest finish time before request timestamp

---

### 10.2 Unauthorized

HTTP status:

    401

Mobile behavior:
- Try refresh token once.
- Retry original request once.
- If refresh fails, logout and route to Login.

---

### 10.3 Runtime not started

HTTP status:

    409

Current backend behavior:
Used when simulator runtime is unavailable.

Mobile message:

    Recommendation runtime is currently unavailable. Please try again after the backend runtime starts.

---

### 10.4 Not found

HTTP status:

    404

Mobile behavior:
Show not-found state and refetch relevant list.

---

### 10.5 Server error

HTTP status:

    500

Mobile behavior:
Show generic backend error. Do not expose internal stack traces.

---

## 11. Mobile implementation rules

### 11.1 Server state

Use TanStack Query for:
- stations
- station details
- recommendations
- reservations
- sessions
- profile

### 11.2 App state

Use Zustand for:
- auth status
- current in-memory access token
- charging request draft
- selected recommendation
- map filters
- theme/demo preferences

### 11.3 Secure storage

Use react-native-keychain for:
- refresh token

Do not store tokens in:
- AsyncStorage
- plain Zustand persistence
- source code
- committed env files

### 11.4 Recommendation retry rule

Do not automatically retry:

    POST /recommendations

Reason:
A retry can inject duplicate live requests into the simulator runtime.

---

## 12. Current vs target backend summary

Exists now:
- GET /
- GET /health
- GET /runtime/status
- GET /runtime/state
- GET /runtime/events
- GET /runtime/recommendations/recent
- GET /stations
- GET /stations/{station_id}
- POST /stations
- PUT /stations/{station_id}
- DELETE /stations/{station_id}
- POST /recommendations

Needs build:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/logout
- GET /auth/me
- POST /reservations
- GET /reservations/me
- PATCH /reservations/{reservation_id}/cancel
- POST /sessions/start
- GET /sessions/active
- POST /sessions/{session_id}/end
- GET /sessions/me

Needs DB replacement:
- stations
- users
- refresh_tokens
- reservations
- charging_sessions
- charging_requests
- recommendation_results

---

## 13. Final contract principle

The mobile app is a user-facing product.

It should:
- send charging requests
- display backend-generated recommendations
- reserve selected station options
- show active and past sessions
- manage profile/auth state

It should not:
- expose simulator internals directly
- calculate recommendations locally
- connect directly to PostgreSQL
- store important state only in memory
- treat runtime/dashboard as part of the user app
