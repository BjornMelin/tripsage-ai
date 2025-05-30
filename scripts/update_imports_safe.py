import ast
import os
import re
from pathlib import Path

# Get list of available modules in tripsage_core
tripsage_core_path = Path("tripsage_core")
core_modules = set()

for root, dirs, files in os.walk(tripsage_core_path):
    # Convert path to module format (tripsage_core.module.submodule)
    rel_path = Path(root).relative_to(tripsage_core_path)
    module_path = "tripsage_core." + ".".join(rel_path.parts)

    # Add directory if it has __init__.py
    if "__init__.py" in files:
        core_modules.add(module_path)

    # Add individual .py files
    for file in files:
        if file.endswith(".py") and file != "__init__.py":
            core_modules.add(f"{module_path}.{file[:-3]}")


def should_update(import_path):
    """Check if import should be updated to tripsage_core"""
    # Check exact module match
    if import_path in core_modules:
        return True

    # Check parent modules
    parts = import_path.split(".")
    for i in range(1, len(parts)):
        parent = ".".join(parts[:i])
        if parent in core_modules:
            return True

    return False


def update_imports_in_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Skipping {file_path} due to encoding issues")
        return False

    # Parse AST to find all imports
    tree = ast.parse(content)
    imports = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    # Update imports that should be changed
    updated = content
    for imp in imports:
        if imp.startswith("tripsage.") and should_update(
            imp.replace("tripsage.", "tripsage_core.")
        ):
            updated = re.sub(
                rf"(from\s+){re.escape(imp)}(\s+import)",
                rf"\1{imp.replace('tripsage.', 'tripsage_core.')}\2",
                updated,
            )
            updated = re.sub(
                rf"(import\s+){re.escape(imp)}",
                rf"\1{imp.replace('tripsage.', 'tripsage_core.')}",
                updated,
            )

    # Write back if changed
    if updated != content:
        with open(file_path, "w") as f:
            f.write(updated)
        return True
    return False


def main():
    updated_count = 0
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                if update_imports_in_file(file_path):
                    print(f"Updated imports in {file_path}")
                    updated_count += 1

    print(f"\nUpdated {updated_count} files")


if __name__ == "__main__":
    main()
