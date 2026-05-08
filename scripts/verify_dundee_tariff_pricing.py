"""Print simple Dundee tariff pricing examples for recommendation-time verification."""

from __future__ import annotations

from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
EV_CORE_SRC = REPO_ROOT / "packages" / "ev_core" / "src"
if str(EV_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(EV_CORE_SRC))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ev_core.pricing.dundee_tariffs import build_dundee_tariff_metadata
from ev_core.pricing.dynamic_pricing import DynamicPricingInput, calculate_dynamic_price


ENERGY_KWH = 20.0


def print_example(label: str, *, connector_type: str, power_kw: float) -> float:
    tariff = build_dundee_tariff_metadata(connector_type=connector_type, power_kw=power_kw)
    pricing = calculate_dynamic_price(
        DynamicPricingInput(
            base_price_per_kwh=float(tariff["base_price_per_kwh"]),
            transformer_capacity_kw=100.0,
            transformer_net_load_kw=60.0,
            transformer_headroom_kw=40.0,
            station_queue_length=0,
            station_utilization=0.0,
            dynamic_pricing_enabled=True,
        )
    )
    estimated_cost = ENERGY_KWH * pricing.dynamic_price_per_kwh
    print(label)
    print(f"  tariff_class: {tariff['tariff_class']}")
    print(f"  base_price_per_kwh: {pricing.base_price_per_kwh:.2f}")
    print(f"  final_price_per_kwh: {pricing.dynamic_price_per_kwh:.2f}")
    print(f"  requested_energy_kwh: {ENERGY_KWH:.1f}")
    print(f"  estimated_cost_gbp: {estimated_cost:.2f}")
    print(
        "  metadata: "
        f"total_dynamic_multiplier={pricing.total_multiplier:.2f}, "
        f"transformer_multiplier={pricing.transformer_multiplier:.2f}, "
        f"congestion_multiplier={pricing.congestion_multiplier:.2f}"
    )
    return estimated_cost


def main() -> int:
    print("Dundee tariff pricing verification")
    costs = [
        print_example("AC Standard", connector_type="AC", power_kw=7.0),
        print_example("AC Fast", connector_type="AC", power_kw=22.0),
        print_example("Rapid", connector_type="Rapid", power_kw=50.0),
        print_example("Ultra Rapid", connector_type="Ultra Rapid", power_kw=150.0),
    ]
    if costs != sorted(costs):
        print("Tariff ordering check failed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
