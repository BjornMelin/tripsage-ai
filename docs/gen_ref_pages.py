#!/usr/bin/env python3
"""Generate the code reference pages and navigation."""

from pathlib import Path

import mkdocs_gen_files
from mkdocs_gen_files.nav import Nav


nav = Nav()

src_paths = [
    Path("tripsage"),
    Path("tripsage_core"),
]

# Modules to skip due to import issues
skip_modules = {
    "tripsage.api.schemas.requests.activities",
    "tripsage.api.schemas.requests.search",
}

# Directories to skip entirely
skip_dirs = {
    "tripsage/api/schemas/requests",
    "tripsage/api/schemas/responses",
    "tripsage/db",
    "tripsage/orchestration",
    "tripsage_core/infrastructure",
    "tripsage_core/observability",
    "tripsage_core/utils",
}

for src_path in src_paths:
    for path in sorted(src_path.rglob("*.py")):
        # Skip entire directories
        if any(skip_dir in str(path) for skip_dir in skip_dirs):
            continue

        module_path = path.relative_to(src_path.parent).with_suffix("")
        doc_path = path.relative_to(src_path.parent).with_suffix(".md")
        full_doc_path = Path("reference", doc_path)

        parts = tuple(module_path.parts)

        if parts[-1] == "__init__":
            parts = parts[:-1]
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")
        elif parts[-1] == "__main__":
            continue

        module_name = ".".join(parts)
        if module_name in skip_modules:
            continue

        nav[parts] = doc_path.as_posix()

        try:
            with mkdocs_gen_files.open(full_doc_path, "w") as fd:
                ident = ".".join(parts)
                fd.write(f"::: {ident}")
        except OSError as e:
            print(f"Warning: Failed to generate docs for {module_name}: {e}")
            continue

        mkdocs_gen_files.set_edit_path(full_doc_path, path)
