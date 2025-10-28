"""Policy test: routers must not declare Pydantic BaseModel classes.

This enforces the design rule that all API request/response models live
under `tripsage/api/schemas` and not in router modules.
"""

from __future__ import annotations

import re
from pathlib import Path


def test_no_pydantic_models_in_routers() -> None:
    """Ensure routers do not declare Pydantic BaseModel subclasses."""
    root = Path("tripsage/api/routers")
    pattern = re.compile(r"^class\s+\w+\(BaseModel\)")

    offenders: list[str] = []
    for py in root.glob("*.py"):
        text = py.read_text(encoding="utf-8")
        offenders.extend(
            f"{py}: {line.strip()}"
            for line in text.splitlines()
            if pattern.search(line.strip())
        )

    assert not offenders, (
        "Routers must not declare Pydantic models; move them to tripsage/api/schemas.\n"
        + "\n".join(offenders)
    )
