#!/usr/bin/env sh
# Backward-compatible entrypoint.
# Wrapper target: scripts/verification/smoke_mobile_lifecycle.sh
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
exec sh "$SCRIPT_DIR/verification/smoke_mobile_lifecycle.sh" "$@"
