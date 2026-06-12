# Models Directory

Trained checkpoints are not committed to GitHub.

Typical local outputs:

```text
models/
  rl/
  rl_feeder/
  rl_feeder_final/
```

The feeder MaskablePPO training script writes:

```text
models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip
```

Use an external artifact store, release asset, or shared drive for trained checkpoints.
