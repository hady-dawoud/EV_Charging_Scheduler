#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
if [[ "$OSTYPE" == "msys"* || "$OSTYPE" == "win32"* ]]; then
  . .venv/Scripts/activate
else
  . .venv/bin/activate
fi

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e packages/ev_core

echo "Setup complete. Activate with: source .venv/bin/activate"
