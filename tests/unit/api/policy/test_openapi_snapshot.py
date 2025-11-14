"""OpenAPI snapshot test to catch accidental contract changes.

Generates the current OpenAPI schema from the app and compares
to a committed golden snapshot. Update the snapshot intentionally
when making additive changes to public contracts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tripsage.api.main import app


def test_openapi_snapshot_matches() -> None:
    """Validate that the generated OpenAPI matches the committed snapshot."""
    client = TestClient(app)
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    current = resp.json()

    snapshot_path = Path("tests/unit/api/policy/openapi_snapshot.json")
    assert snapshot_path.exists(), (
        "OpenAPI snapshot missing. Generate with: "
        "python -c 'from tripsage.api.main import app; import json; "
        "print(json.dumps(app.openapi(), indent=2))' "
        "> tests/unit/api/policy/openapi_snapshot.json"
    )
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    # Exclude endpoints migrated to Next.js AI SDK v6 agents.
    def _strip_migrated_paths(
        spec: dict[str, dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        paths = dict(spec.get("paths", {}))
        filtered = {
            k: v
            for k, v in paths.items()
            if not (k.startswith(("/api/chat", "/api/search", "/api/destinations")))
        }
        spec = dict(spec)
        spec["paths"] = filtered
        return spec

    current = _strip_migrated_paths(current)
    snapshot = _strip_migrated_paths(snapshot)

    assert current == snapshot, (
        "OpenAPI schema changed. If intentional (additive and approved), "
        "update the snapshot."
    )
