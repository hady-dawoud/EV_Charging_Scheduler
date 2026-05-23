#!/usr/bin/env bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://localhost:8000}"
CHARGER_EVENT_SECRET="${CHARGER_EVENT_SECRET:-change_me_charger_event_secret}"
STATION_ID="${STATION_ID:-gellatly_street_car_park_dundee}"
PASSWORD="${PASSWORD:-password123}"
EMAIL="smoke.mobile.$(date +%s)@example.com"

json_get() {
  python -c "import json,sys; data=json.load(sys.stdin); cur=data
for part in sys.argv[1].split('.'):
    cur=cur[part]
print(cur)" "$1"
}

iso_plus_minutes() {
  python - "$1" <<'PY'
from datetime import datetime, timedelta, timezone
import sys

minutes = int(sys.argv[1])
print((datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z"))
PY
}

echo "API_BASE_URL=$API_BASE_URL"
echo "STATION_ID=$STATION_ID"
echo "Registering smoke user: $EMAIL"

AUTH_RESPONSE="$(
  curl -sS -f -X POST "$API_BASE_URL/auth/register" \
    -H "Content-Type: application/json" \
    -d "{\"full_name\":\"Smoke Mobile Lifecycle\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}"
)"

ACCESS_TOKEN="$(printf '%s' "$AUTH_RESPONSE" | json_get access_token)"
echo "Auth OK"

START_AT="$(iso_plus_minutes 5)"
UNTIL_AT="$(iso_plus_minutes 35)"

echo "Creating reservation"

RESERVATION_RESPONSE="$(
  curl -sS -f -X POST "$API_BASE_URL/reservations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
      \"station_id\":\"$STATION_ID\",
      \"client_request_id\":\"smoke-mobile-lifecycle\",
      \"request_id\":\"smoke-runtime-request\",
      \"recommendation_rank\":1,
      \"reserved_start_at\":\"$START_AT\",
      \"reserved_until\":\"$UNTIL_AT\",
      \"estimated_cost_gbp\":7.4,
      \"estimated_duration_minutes\":30,
      \"charger_label\":\"rapid\",
      \"distance_km\":0.5,
      \"score\":0.75
    }"
)"

RESERVATION_ID="$(printf '%s' "$RESERVATION_RESPONSE" | json_get reservation_id)"
echo "Reservation OK: $RESERVATION_ID"

echo "Starting charger-side session"

START_RESPONSE="$(
  curl -sS -f -X POST "$API_BASE_URL/charger-events/sessions/start" \
    -H "Content-Type: application/json" \
    -H "X-Charger-Event-Secret: $CHARGER_EVENT_SECRET" \
    -d "{\"reservation_id\":\"$RESERVATION_ID\",\"connector_type\":\"rapid\",\"charger_power_kw\":50}"
)"

SESSION_ID="$(printf '%s' "$START_RESPONSE" | json_get session_id)"
SESSION_STATUS="$(printf '%s' "$START_RESPONSE" | json_get status)"
test "$SESSION_STATUS" = "active"
echo "Session active OK: $SESSION_ID"

echo "Completing charger-side session"

COMPLETE_RESPONSE="$(
  curl -sS -f -X POST "$API_BASE_URL/charger-events/sessions/$SESSION_ID/complete" \
    -H "Content-Type: application/json" \
    -H "X-Charger-Event-Secret: $CHARGER_EVENT_SECRET" \
    -d "{\"energy_kwh\":18.5,\"cost_total\":7.40}"
)"

COMPLETE_STATUS="$(printf '%s' "$COMPLETE_RESPONSE" | json_get status)"
test "$COMPLETE_STATUS" = "completed"
echo "Session completed OK"

echo "Verifying /sessions/me contains completed session"

SESSIONS_RESPONSE="$(
  curl -sS -f -X GET "$API_BASE_URL/sessions/me" \
    -H "Authorization: Bearer $ACCESS_TOKEN"
)"

SESSIONS_JSON="$SESSIONS_RESPONSE" SESSION_ID="$SESSION_ID" python - <<'PY'
import json
import os

payload = json.loads(os.environ["SESSIONS_JSON"])
session_id = os.environ["SESSION_ID"]
sessions = payload["sessions"]

if not any(s["session_id"] == session_id and s["status"] == "completed" for s in sessions):
    raise SystemExit("completed session not found in /sessions/me")

print("sessions/me completed verification OK")
PY

echo "Creating second reservation for expiry rejection test"

EXPIRE_START_AT="$(iso_plus_minutes 5)"
EXPIRE_UNTIL_AT="$(iso_plus_minutes 35)"

EXPIRE_RESERVATION_RESPONSE="$(
  curl -sS -f -X POST "$API_BASE_URL/reservations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -d "{
      \"station_id\":\"$STATION_ID\",
      \"client_request_id\":\"smoke-expiry\",
      \"request_id\":\"smoke-expiry-request\",
      \"recommendation_rank\":1,
      \"reserved_start_at\":\"$EXPIRE_START_AT\",
      \"reserved_until\":\"$EXPIRE_UNTIL_AT\",
      \"estimated_cost_gbp\":7.4,
      \"estimated_duration_minutes\":30,
      \"charger_label\":\"rapid\",
      \"distance_km\":0.5,
      \"score\":0.75
    }"
)"

EXPIRE_RESERVATION_ID="$(printf '%s' "$EXPIRE_RESERVATION_RESPONSE" | json_get reservation_id)"
echo "Expiry test reservation: $EXPIRE_RESERVATION_ID"

if docker exec ev_postgres psql -U ev_user -d ev_smart_charging -c "update reservations set status='confirmed', reserved_until=now() - interval '20 minutes' where reservation_id='$EXPIRE_RESERVATION_ID';" >/dev/null 2>&1; then
  echo "Forced reservation into expired window"

  set +e
  EXPIRED_START_RESPONSE="$(
    curl -sS -i -X POST "$API_BASE_URL/charger-events/sessions/start" \
      -H "Content-Type: application/json" \
      -H "X-Charger-Event-Secret: $CHARGER_EVENT_SECRET" \
      -d "{\"reservation_id\":\"$EXPIRE_RESERVATION_ID\"}"
  )"
  set -e

  printf '%s' "$EXPIRED_START_RESPONSE" | grep -q "409 Conflict"
  printf '%s' "$EXPIRED_START_RESPONSE" | grep -q "Reservation is expired"
  echo "Expired reservation rejection OK"
else
  echo "Skipping DB-forced expiry test because ev_postgres is unavailable"
fi

echo "Smoke lifecycle PASS"
