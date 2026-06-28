from __future__ import annotations

import json

from common import get_json


def main() -> None:
    data = get_json("/runtime/recommendations/recent?limit=1")
    print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()
