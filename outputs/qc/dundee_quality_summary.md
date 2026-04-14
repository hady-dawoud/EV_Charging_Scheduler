# Dundee Quality Summary

## Overview

- Total rows in clean file: 387,843
- Total rows in model_ready file: 377,070
- Number removed: 10,773

## Model Filter Counts

- Missing arrival timestamps: 0
- Missing or nonpositive session minutes: 8,096
- Missing or nonpositive energy: 4,266
- Implied power above connector tolerance: 643

Counts above are not mutually exclusive.

## QC Flag Counts

```text
                                    flag  count
                     flag_missing_energy   3064
                  flag_missing_departure      9
               flag_nonpositive_duration   8087
                 flag_nonpositive_energy   1202
            flag_extreme_duration_gt_24h      0
            flag_extreme_duration_gt_48h      0
flag_implied_power_above_connector_limit    643
                flag_cp_id_multi_station   5975
```

## Top Stations By Sessions

```text
                             station_name  sessions_total  cp_count_total
      Princes Street Charging Hub, Dundee          100602               9
Lochee Charging Hub, Aimer Square, Dundee           95077              12
        Queen Street Charging Hub, Dundee           68702              10
                Clepington Road - 4th Hub           50449               6
                 Dundee Ice Arena, Dundee            9294               2
         Gellatly Street Car Park, Dundee            8688              13
            Greenmarket 150kW Bus Charger            8512               2
Greenmarket Multi Storey Car Park, Dundee            5851               5
     South Tay Street (Car Club / Public)            4367               1
                      Dock Street, Dundee            3521               1
```

## Top Stations By Charge Point Count

```text
                              station_name  cp_count_total  sessions_total
          Gellatly Street Car Park, Dundee              13            8688
 Lochee Charging Hub, Aimer Square, Dundee              12           95077
         Queen Street Charging Hub, Dundee              10           68702
       Princes Street Charging Hub, Dundee               9          100602
                 Clepington Road - 4th Hub               6           50449
 Greenmarket Multi Storey Car Park, Dundee               5            5851
     Olympia Multi-Storey Car Park, Dundee               4            2888
                  Dundee Ice Arena, Dundee               2            9294
             Greenmarket 150kW Bus Charger               2            8512
Whitfield Centre, Lothian Crescent, Dundee               2            2827
```

## Suspicious Records Notes

- cp_id values attached to multiple station_ids: 3
- Conflicting cp_id list: 52399, 60662, APT50348
- Rows with durations above 24 hours: 0
- Rows with durations above 48 hours: 0
- Rows with missing departure timestamps: 9
- Map rendering method: fallback_scatter

## Generated Plots

- `outputs/figures/dundee_demand_growth_sessions_by_year.png`
- `outputs/figures/dundee_energy_by_year_kwh.png`
- `outputs/figures/dundee_daily_energy_2024_bar.png`
- `outputs/figures/dundee_hourly_load_profile_bar.png`
- `outputs/figures/dundee_station_map.png`
- `outputs/figures/dundee_station_map_colored_by_cp_count.png`
- `outputs/figures/dundee_station_map_colored_by_sessions.png`
