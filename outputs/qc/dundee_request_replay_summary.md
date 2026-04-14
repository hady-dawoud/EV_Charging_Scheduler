# Dundee Request Replay Summary

## Request Counts By Year

| year | request_count |
| --- | ---: |
| 2023 | 117701 |
| 2024 | 90320 |

## Requests By Zone

| zone_id | zone_name | request_count |
| --- | --- | ---: |
| zone_central_waterfront | Central Waterfront & City Core | 71574 |
| zone_west_lochee | West Lochee & Camperdown | 57403 |
| zone_north_inner | North Inner Residential | 40782 |
| zone_east_corridor | East Corridor & Broughty | 38262 |

## Requests By Station

| station_id | station_name | request_count |
| --- | --- | ---: |
| princes_street_charging_hub_dundee | Princes Street Charging Hub, Dundee | 50817 |
| lochee_charging_hub_aimer_square_dundee | Lochee Charging Hub, Aimer Square, Dundee | 49129 |
| clepington_road_4th_hub | Clepington Road - 4th Hub | 36994 |
| queen_street_charging_hub_dundee | Queen Street Charging Hub, Dundee | 33859 |
| greenmarket_150kw_bus_charger | Greenmarket 150kW Bus Charger | 5688 |
| dundee_ice_arena_dundee | Dundee Ice Arena, Dundee | 5258 |
| gellatly_street_car_park_dundee | Gellatly Street Car Park, Dundee | 4199 |
| greenmarket_multi_storey_car_park_dundee | Greenmarket Multi Storey Car Park, Dundee | 2538 |
| south_tay_street_car_club_public | South Tay Street (Car Club / Public) | 2434 |
| michelin_scotland_innovation_park | Michelin Scotland Innovation Park | 1582 |
| dock_street_dundee | Dock Street, Dundee | 1498 |
| orleans_place_dundee | Orleans Place, Dundee | 1259 |
| alexander_street_dundee | Alexander Street - Dundee | 1233 |
| whitfield_centre_lothian_crescent_dundee | Whitfield Centre, Lothian Crescent, Dundee | 1204 |
| dundee_taybridge_rail_station_south_union_street_dundee | Dundee Taybridge Rail Station, South Union Street, Dundee | 1140 |
| nethergate_dundee | Nethergate, Dundee | 1028 |
| olympia_multi_storey_car_park_dundee | Olympia Multi-Storey Car Park, Dundee | 990 |
| housing_office_east_midmill_road_dundee | Housing Office East, Midmill Road, Dundee | 875 |
| camperdown_country_park | Camperdown Country Park | 840 |
| olympia_hub | Olympia Hub | 722 |
| eastern_primary_school | Eastern Primary School | 677 |
| craigowen_road | Craigowen Road | 648 |
| rpc_dundee | RPC Dundee | 639 |
| dawson_park_broughty_ferry | Dawson Park, Broughty Ferry | 605 |
| derby_street | Derby Street | 564 |
| dundee_house_depot_north_lindsay_street_dundee | Dundee House Depot, North Lindsay Street, Dundee | 322 |
| caird_avenue | Caird Avenue | 316 |
| douglas_community_library | Douglas Community Library | 271 |
| deveron_terrace | Deveron Terrace | 158 |
| mill_o_mains_primary_school | Mill O Mains Primary School | 158 |
| dundee_railway_station | Dundee Railway Station | 148 |
| menzieshill_community_centre | Menzieshill Community Centre | 111 |
| balmerino_road | Balmerino Road | 64 |
| trades_lane_dundee | Trades Lane, Dundee | 50 |
| coldside_nursery | Coldside Nursery | 3 |

## Arrival Histogram Summary

| arrival_hour | share |
| --- | ---: |
| 00 | 0.0186 |
| 01 | 0.0217 |
| 02 | 0.0142 |
| 03 | 0.0114 |
| 04 | 0.0119 |
| 05 | 0.0119 |
| 06 | 0.0143 |
| 07 | 0.0291 |
| 08 | 0.0433 |
| 09 | 0.0596 |
| 10 | 0.0641 |
| 11 | 0.0708 |
| 12 | 0.0726 |
| 13 | 0.0739 |
| 14 | 0.0720 |
| 15 | 0.0666 |
| 16 | 0.0603 |
| 17 | 0.0547 |
| 18 | 0.0495 |
| 19 | 0.0495 |
| 20 | 0.0467 |
| 21 | 0.0365 |
| 22 | 0.0248 |
| 23 | 0.0221 |

## Requested Energy Summary

| metric | value |
| --- | ---: |
| count | 208021 |
| mean | 22.738 |
| median | 16.704 |
| std | 30.125 |
| min | 0.001 |
| p10 | 5.134 |
| p25 | 9.867 |
| p75 | 26.226 |
| p90 | 38.823 |
| p95 | 48.133 |
| max | 329.584 |

## Slack-Time Summary

| metric | value |
| --- | ---: |
| count | 208021 |
| mean | 41.222 |
| median | 15.0 |
| std | 101.101 |
| min | 0.0 |
| p10 | 0.0 |
| p25 | 15.0 |
| p75 | 30.0 |
| p90 | 60.0 |
| p95 | 120.0 |
| max | 1425.0 |

## Dropped Sessions

| request_year | drop_reason | count |
| --- | --- | ---: |
| 2023 | excluded_by_model_ready_qc | 1349 |
| 2023 | technical_duration_exceeds_window | 15 |
| 2024 | excluded_by_model_ready_qc | 4324 |
| 2024 | technical_duration_exceeds_window | 17 |
