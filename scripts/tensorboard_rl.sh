#!/usr/bin/env bash
set -euo pipefail

tensorboard --logdir outputs/rl_feeder/tensorboard_final --port "${TENSORBOARD_PORT:-6007}"
