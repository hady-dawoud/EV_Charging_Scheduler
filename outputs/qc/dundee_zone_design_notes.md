# Dundee Zone Design Notes

This topology is a simulator scaffold for V1. It is not verified SSEN network truth and should not be treated as a real feeder map.

## Zone Definitions
### Central Waterfront & City Core (`zone_central_waterfront`)
- Stations: 13
- CP count proxy: 41
- Assumed station capacity total: 1370 kW
- Why this zone: Grouped as the dense central charging core around the waterfront corridor and adjacent city-centre streets.

### East Corridor & Broughty (`zone_east_corridor`)
- Stations: 7
- CP count proxy: 18
- Assumed station capacity total: 570 kW
- Why this zone: Grouped as the eastern corridor spanning the major Queen Street hub and the outer eastern neighbourhood sites.

### North Inner Residential (`zone_north_inner`)
- Stations: 8
- CP count proxy: 14
- Assumed station capacity total: 570 kW
- Why this zone: Grouped as the inner northern residential belt linking Coldside/Clepington with Midmill and Mid Craigie.

### West Lochee & Camperdown (`zone_west_lochee`)
- Stations: 7
- CP count proxy: 20
- Assumed station capacity total: 700 kW
- Why this zone: Grouped as the western corridor around the Lochee hub, western residential sites, and Camperdown/Ice Arena activity.

## Transformer Design
- Transformer count: 8
- Each station is assigned to exactly one synthetic transformer so the simulator has a single upstream attachment point per station.
- The transformer count was chosen to keep the topology simple enough for V1 while still separating the biggest hubs into distinct local groups.

## Capacity Assumptions
- Station capacity uses `cp_count_total` as the default port-count proxy at 22 kW per port.
- Rapid and ultra-rapid sites also use the station connected-power proxy, diversified before rounding to avoid assuming full simultaneous nameplate draw.
- Formula: `station_capacity_kw_assumed = round_up(max(cp_count_total * 22, station_max_power_kw_proxy * station_diversity_factor), 10)`.
- Transformer capacity uses the sum of attached station capacities with a 15% diversity margin before rounding to the next 50 kW.
- All transformer and feeder IDs here are synthetic planning assumptions for simulator V1 only.

## Largest Synthetic Transformers

| transformer_id | transformer_name | zone_id | stations | assumed_capacity_kw |
| --- | --- | --- | ---: | ---: |
| tx_central_waterfront | Central Waterfront Feeder | zone_central_waterfront | 7 | 750 |
| tx_west_lochee | West Lochee Feeder | zone_west_lochee | 5 | 500 |
| tx_central_market | Central Market Feeder | zone_central_waterfront | 6 | 450 |
| tx_east_queen_street | East Queen Street Feeder | zone_east_corridor | 3 | 400 |
| tx_north_clepington | North Clepington Feeder | zone_north_inner | 4 | 400 |
| tx_east_broughty | East Broughty Feeder | zone_east_corridor | 4 | 150 |
| tx_north_midcraigie | North Mid Craigie Feeder | zone_north_inner | 4 | 150 |
| tx_west_camperdown | West Camperdown Feeder | zone_west_lochee | 2 | 150 |

## Stations Still Needing Location Follow-up

- `Alexander Street - Dundee` (`alexander_street_dundee`): Current point is a postcode centroid rather than a charger-level placement.
- `Caird Avenue` (`caird_avenue`): Current point is a low-confidence road-only match with no postcode in the source data.
- `Camperdown Country Park` (`camperdown_country_park`): Current point is a park feature centroid and may not align with the charger bays.
- `Clepington Road - 4th Hub` (`clepington_road_4th_hub`): Current point is a postcode centroid for a major hub and should be pinned more precisely.
- `Dundee Taybridge Rail Station, South Union Street, Dundee` (`dundee_taybridge_rail_station_south_union_street_dundee`): Current point shares the railway-station location and should be confirmed at site level.
- `Greenmarket 150kW Bus Charger` (`greenmarket_150kw_bus_charger`): Current point is a postcode centroid for a high-power bus charger and should be manually pinned.
- `Housing Office East, Midmill Road, Dundee` (`housing_office_east_midmill_road_dundee`): Current point is a postcode centroid and should be confirmed against the exact site frontage.

## Explicit Scope Note
- This Dundee zone and transformer layer is a simulator-ready abstraction for V1 and is not intended to represent verified utility transformer placements, feeder routes, or DNO asset names.
