# Dundee Request Replay Notes

These Dundee replay requests are derived from the model-ready session table and mapped onto the simulator zone/transformer topology using 15-minute slot alignment.

## Replay Construction
- One replay request is generated per usable Dundee charging session in 2023 or 2024.
- `arrival_ts` preserves the observed timestamp, while `arrival_slot` floors to the 15-minute simulator time base.
- `latest_finish_ts` uses the observed approximate departure timestamp, while `latest_finish_slot` rounds that deadline up to the 15-minute time base.
- `requested_energy_kwh` equals the observed delivered session energy from the model-ready dataset.
- `requested_duration_minutes` starts from the technical minimum charging time at the observed connector limit and then uses a deterministic preference-based share of the remaining observed dwell slack.

## Preference Heuristics
- User preference modes are assigned deterministically via a SHA-256 hash bucket keyed by `session_id` and `connector_type`.
- AC sessions use the heuristic distribution `closest 50% / cheapest 35% / fastest 15%`.
- Rapid sessions use `closest 25% / cheapest 15% / fastest 60%`.
- Ultra-rapid sessions use `closest 15% / cheapest 10% / fastest 75%`.
- Charger type preference maps directly from connector type when known, otherwise `Any`.

## Replay Priors Captured
- Arrival hour distribution: 24 hourly buckets.
- Weekday/weekend split: `{'weekday': 0.712144, 'weekend': 0.287856}`.
- Month share: `{1: 0.09674, 2: 0.089577, 3: 0.093279, 4: 0.079473, 5: 0.078247, 6: 0.07394, 7: 0.074132, 8: 0.077127, 9: 0.080429, 10: 0.072531, 11: 0.090606, 12: 0.093918}`.
- Zone request share: `{'zone_central_waterfront': 0.344071, 'zone_east_corridor': 0.183933, 'zone_north_inner': 0.196048, 'zone_west_lochee': 0.275948}`.

## Exogenous Tables
- `background_load_15min.csv` is a transformer-level deterministic profile scaled by synthetic transformer capacity and adjusted by time of day, weekday/weekend, zone, and season.
- `price_table_15min.csv` is a Dundee-wide deterministic TOU tariff in GBP/kWh on the same 15-minute time base.
- `pv_profile_15min.csv` is an optional normalized daylight-shaped PV capacity-factor profile on the same time base.

## Dropped Sessions
- 2023 / `excluded_by_model_ready_qc`: 1349
- 2023 / `technical_duration_exceeds_window`: 15
- 2024 / `excluded_by_model_ready_qc`: 4324
- 2024 / `technical_duration_exceeds_window`: 17
