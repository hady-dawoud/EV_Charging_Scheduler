#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

FEEDER_RL_DATA_DIR="${FEEDER_RL_DATA_DIR:-$REPO_ROOT/../../../outputs/evside_feeder_rl}"
CHECKPOINT_PATH="${CHECKPOINT_PATH:-$REPO_ROOT/models/rl_feeder_final/maskable_ppo_feeder_station_selector.zip}"

python scripts/rl_training/evaluate_maskable_ppo_feeder_station_selector.py \
  --feeder-rl-data-dir "$FEEDER_RL_DATA_DIR" \
  --checkpoint-path "$CHECKPOINT_PATH" \
  --policy "${POLICY:-checkpoint}" \
  --grid-advisory-mode recorded \
  --grid-evaluation-mode replay \
  --min-truth-level area_pf \
  --exclude-adapter-proxy \
  --require-replay-covered-area \
  --output-json outputs/rl_feeder/evaluation_${POLICY:-checkpoint}.json \
  --output-csv outputs/rl_feeder/evaluation_runs.csv
