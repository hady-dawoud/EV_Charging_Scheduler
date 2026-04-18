"""Export sample standalone request and recommendation contracts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from services.sim_runtime.demo import build_sample_request  # noqa: E402
from services.sim_runtime.runtime_manager import RuntimeManager  # noqa: E402


def main() -> None:
    output_dir = REPO_ROOT / "outputs" / "runtime"
    output_dir.mkdir(parents=True, exist_ok=True)
    runtime = RuntimeManager(REPO_ROOT)

    request = build_sample_request()
    request_path = output_dir / "sample_external_request.json"
    request_path.write_text(request.model_dump_json(indent=2) + "\n", encoding="utf-8")

    recommendation = runtime.recommend(request)
    recommendation_path = output_dir / "sample_recommendation_response.json"
    recommendation_path.write_text(recommendation.model_dump_json(indent=2) + "\n", encoding="utf-8")

    manifest = {
        "sample_external_request": str(request_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "sample_recommendation_response": str(recommendation_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    manifest_path = output_dir / "sample_contract_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
