# Dundee Station Location Review Summary

This layer preserves the original station location seeds and adds a reproducible manual-override workflow.

## Counts
- Total stations: 35
- `accepted_current`: 28
- `manually_overridden`: 0
- `needs_followup`: 7
- Override workflow file: `data/processed/station_location_overrides.csv`

## Review Basis
- Original location source and confidence from `station_locations.csv` were preserved.
- Existing Dundee interactive maps were used as the visual-review artifacts that motivate this workflow.
- Any station still marked `needs_followup` keeps its current coordinates as a temporary simulator placeholder until a manual override is supplied.

## Review Artifacts
- `outputs/maps/dundee_station_map_interactive.html`
- `outputs/maps/dundee_station_map_interactive_by_cp_count.html`
- `outputs/maps/dundee_station_map_interactive_by_sessions.html`

## Stations Still Needing Follow-up

| station_id | station_name | current_source | confidence | reason |
| --- | --- | --- | --- | --- |
| alexander_street_dundee | Alexander Street - Dundee | postcodes_io_centroid | medium | Current point is a postcode centroid rather than a charger-level placement. |
| caird_avenue | Caird Avenue | osm_road_match | low | Current point is a low-confidence road-only match with no postcode in the source data. |
| camperdown_country_park | Camperdown Country Park | osm_named_feature | medium | Current point is a park feature centroid and may not align with the charger bays. |
| clepington_road_4th_hub | Clepington Road - 4th Hub | postcodes_io_centroid | medium | Current point is a postcode centroid for a major hub and should be pinned more precisely. |
| dundee_taybridge_rail_station_south_union_street_dundee | Dundee Taybridge Rail Station, South Union Street, Dundee | manual_shared_site | medium | Current point shares the railway-station location and should be confirmed at site level. |
| greenmarket_150kw_bus_charger | Greenmarket 150kW Bus Charger | postcodes_io_centroid | medium | Current point is a postcode centroid for a high-power bus charger and should be manually pinned. |
| housing_office_east_midmill_road_dundee | Housing Office East, Midmill Road, Dundee | postcodes_io_centroid | medium | Current point is a postcode centroid and should be confirmed against the exact site frontage. |
