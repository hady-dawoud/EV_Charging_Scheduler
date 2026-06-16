#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

python -m pytest tests/grid_advisory tests/rl_feeder tests/rl_training -q

FEEDER_RL_DATA_DIR="${FEEDER_RL_DATA_DIR:-$REPO_ROOT/../../../outputs/evside_feeder_rl}"
if [[ -f "$FEEDER_RL_DATA_DIR/feeder_ev_action_catalog.parquet" || -f "$FEEDER_RL_DATA_DIR/feeder_ev_action_catalog.csv" ]]; then
  python scripts/rl_training/train_maskable_ppo_feeder_station_selector.py \
    --feeder-rl-data-dir "$FEEDER_RL_DATA_DIR" \
    --grid-advisory-mode disabled \
    --scenario-count 2 \
    --duration-hours 1 \
    --dry-run
else
  echo "Skipping feeder RL dry-run; set FEEDER_RL_DATA_DIR to a restored feeder RL export package."
fi
