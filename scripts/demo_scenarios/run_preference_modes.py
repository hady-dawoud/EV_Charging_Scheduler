from __future__ import annotations

from common import mobile_payload, post_json, print_top_summary


def main() -> None:
    for preference in ["cheapest", "fastest", "closest"]:
        print("\n==", preference.upper(), "==")
        payload = mobile_payload(preference)
        result = post_json("/mobile/recommendations", payload)
        print_top_summary(result)


if __name__ == "__main__":
    main()
