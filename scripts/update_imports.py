import os
import re


def update_imports_in_file(file_path):
    with open(file_path, "r") as f:
        content = f.read()

    # Replace tripsage imports with tripsage_core
    updated = re.sub(r"from\s+tripsage(\.|$)", r"from tripsage_core\1", content)
    updated = re.sub(r"import\s+tripsage(\.|$)", r"import tripsage_core\1", updated)

    # Update specific imports
    updated = re.sub(
        r"from tripsage_core\.agents\.base import",
        "from tripsage.agents.base import",
        updated,
    )
    updated = re.sub(
        r"from tripsage_core\.agents\.handoffs import",
        "from tripsage.agents.handoffs import",
        updated,
    )

    with open(file_path, "w") as f:
        f.write(updated)


def main():
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                print(f"Updating {file_path}")
                update_imports_in_file(file_path)


if __name__ == "__main__":
    main()
