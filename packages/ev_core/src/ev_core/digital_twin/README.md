# ev_core.digital_twin

This package is the app-facing boundary for simulator runtime and digital twin concerns.

Scope:
- Runtime-oriented abstractions used by API/dashboard-facing flows.
- Interfaces that can evolve without coupling training code to app services.

Non-goals:
- Offline RL/MARL training loops.
- Benchmark adapter implementations.
- Checkpoint deployment and inference registry wiring.
