#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

FEEDER_RL_DATA_DIR="${FEEDER_RL_DATA_DIR:-$REPO_ROOT/../../../outputs/evside_feeder_rl}"

python scripts/rl_training/train_maskable_ppo_feeder_station_selector.py \
  --feeder-rl-data-dir "$FEEDER_RL_DATA_DIR" \
  --output-dir models/rl_feeder_final \
  --tensorboard-log outputs/rl_feeder/tensorboard_final \
  --grid-advisory-mode recorded \
  --grid-evaluation-mode replay \
  --request-prior-sources dundee,acn,digitaltwin \
  --min-truth-level area_pf \
  --exclude-adapter-proxy \
  --require-replay-covered-area \
  --scenario-count "${SCENARIO_COUNT:-512}" \
  --duration-hours "${DURATION_HOURS:-24}" \
  --total-timesteps "${TOTAL_TIMESTEPS:-2000000}" \
  --checkpoint-freq "${CHECKPOINT_FREQ:-50000}"
