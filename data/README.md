# Data Directory

This repository intentionally does not include raw, processed, or replay data.

Expected local layout after restoring data from an external source:

```text
data/
  raw/
    dundee/
    acn/
    external/
  interim/
  processed/
    routing/
    topology_scenarios/
```

For feeder-aligned RL, the main DigitalTwin export is expected outside this repo at:

```text
A:/coding/Projects/USSEE/Implementations/DigitalTwin.2.0/outputs/evside_feeder_rl
```

Generated data, request replay tables, station catalogs, TensorBoard logs, and trained models are ignored by Git.
