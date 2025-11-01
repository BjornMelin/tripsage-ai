#!/usr/bin/env python3
"""Script to generate OpenAPI spec from FastAPI app."""

import json
from pathlib import Path

from tripsage.api.main import app


def generate_openapi_spec():
    """Generate and save OpenAPI spec to docs/openapi.json."""
    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(exist_ok=True)

    spec = app.openapi()
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    print(f"✅ OpenAPI spec generated at {output_path}")


if __name__ == "__main__":
    generate_openapi_spec()
