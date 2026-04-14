# Simulator Runtime

This standalone runtime manages the Dundee EV-side simulator outside `apps/**`.

It is intentionally separate from the existing API/mobile prototype layers. The runtime:

- loads the Dundee replay and exogenous 15-minute inputs
- maintains a resumable `DundeeEnv`
- persists runtime state, metrics, recommendations, and events under `outputs/runtime/`
- accepts local external-style request injection through standalone scripts or the runtime CLI

Future API/mobile integration should bind to the contracts in `packages/ev_core/src/ev_core/contracts/` rather than importing anything from `apps/**`.
