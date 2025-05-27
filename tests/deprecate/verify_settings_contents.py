#!/usr/bin/env python
"""Simple script to verify settings.py contents without importing it."""

import re
import sys
from pathlib import Path

# Path to the settings.py file
settings_path = Path(__file__).parent.parent.parent / "src" / "utils" / "settings.py"


def check_class_exists(content, class_name):
    """Check if a class exists in the file content."""
    pattern = rf"class\s+{class_name}\s*\("
    match = re.search(pattern, content)
    return match is not None


def check_attr_exists(content, class_name, attr_name):
    """Check if an attribute exists in a class."""
    # This is a simple regex to find the attribute in the class
    # It's not perfect but should work for our needs
    class_pattern = rf"class\s+{class_name}\s*\(.*?\)\s*:"
    class_match = re.search(class_pattern, content, re.DOTALL)

    if class_match:
        class_start = class_match.start()
        # Find the next class definition
        next_class = re.search(r"class\s+", content[class_start + 1 :])
        if next_class:
            class_end = class_start + 1 + next_class.start()
        else:
            class_end = len(content)

        class_content = content[class_start:class_end]
        attr_pattern = rf"{attr_name}\s*:"
        return re.search(attr_pattern, class_content) is not None

    return False


def check_app_settings_attr(content, attr_name):
    """Check if an attribute exists in the AppSettings class."""
    pattern = rf"{attr_name}\s*:\s*\w+\s*=\s*\w+"
    return re.search(pattern, content) is not None


def main():
    try:
        # Read the file content
        with open(settings_path, "r") as f:
            content = f.read()

        # Check for MCP configuration classes
        classes_to_check = [
            "WebCrawlMCPConfig",
            "PlaywrightMCPConfig",
            "StagehandMCPConfig",
            "TimeMCPConfig",
            "DockerMCPConfig",
            "OpenAPIMCPConfig",
        ]

        # Check for required attributes in each class
        class_attrs = {
            "WebCrawlMCPConfig": [
                "crawl4ai_api_key",
                "crawl4ai_auth_token",
                "crawl4ai_timeout",
                "crawl4ai_max_depth",
                "crawl4ai_default_format",
            ],
            "PlaywrightMCPConfig": ["headless", "browser_type", "timeout"],
            "StagehandMCPConfig": [
                "browserbase_api_key",
                "browserbase_project_id",
                "recovery_enabled",
            ],
            "TimeMCPConfig": [
                "default_timezone",
                "use_system_timezone",
                "format_24_hour",
            ],
            "DockerMCPConfig": ["image_registry", "socket_path", "max_container_count"],
            "OpenAPIMCPConfig": [
                "schema_url",
                "authentication_type",
                "default_timeout",
            ],
        }

        # Check for attributes in AppSettings
        app_settings_attrs = [
            "playwright_mcp",
            "stagehand_mcp",
            "docker_mcp",
            "openapi_mcp",
        ]

        # Run the checks
        all_checks_passed = True

        print("Checking for MCP configuration classes:")
        for class_name in classes_to_check:
            if check_class_exists(content, class_name):
                print(f"✓ {class_name} exists")
            else:
                print(f"✗ {class_name} does not exist")
                all_checks_passed = False

        print("\nChecking for required attributes in each class:")
        for class_name, attrs in class_attrs.items():
            print(f"\n{class_name} attributes:")
            for attr in attrs:
                if check_attr_exists(content, class_name, attr):
                    print(f"  ✓ {attr} exists")
                else:
                    print(f"  ✗ {attr} does not exist")
                    all_checks_passed = False

        print("\nChecking for MCP attributes in AppSettings:")
        for attr in app_settings_attrs:
            if check_app_settings_attr(content, attr):
                print(f"✓ {attr} exists in AppSettings")
            else:
                print(f"✗ {attr} does not exist in AppSettings")
                all_checks_passed = False

        if all_checks_passed:
            print("\nAll checks passed!")
            return 0
        else:
            print("\nSome checks failed.")
            return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
