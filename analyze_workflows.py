#!/usr/bin/env python3
import os

import yaml


def analyze_workflows():
    workflows = {}
    workflow_dir = ".github/workflows"

    for filename in os.listdir(workflow_dir):
        if filename.endswith(".yml") or filename.endswith(".yaml"):
            with open(f"{workflow_dir}/{filename}", "r") as f:
                content = yaml.safe_load(f)
                # Handle the fact that 'on' becomes True in YAML parsing
                triggers = content.get("on", content.get(True, {}))
                workflows[filename] = {
                    "name": content.get("name", "Unnamed"),
                    "triggers": triggers,
                    "jobs": list(content.get("jobs", {}).keys()),
                    "permissions": content.get("permissions", {}),
                    "env": content.get("env", {}),
                    "services_used": [],
                    "raw_triggers": triggers,
                }

                # Check for services in jobs
                for job_name, job_config in content.get("jobs", {}).items():
                    if "services" in job_config:
                        workflows[filename]["services_used"].extend(
                            job_config["services"].keys()
                        )

    print("=== CI/CD WORKFLOW ANALYSIS ===\n")

    for filename, info in workflows.items():
        print(f"📄 {filename}")
        print(f"   Name: {info['name']}")
        print(f"   Jobs: {', '.join(info['jobs'])}")
        print(f"   Triggers: {', '.join(info['raw_triggers'].keys())}")
        if info["raw_triggers"]:
            for trigger, config in info["raw_triggers"].items():
                if isinstance(config, dict):
                    print(f"      {trigger}: {config}")
                else:
                    print(f"      {trigger}: enabled")
        if info["services_used"]:
            print(f"   Services: {', '.join(set(info['services_used']))}")
        print()

    # Check for trigger conflicts
    print("=== TRIGGER PATTERN ANALYSIS ===\n")

    push_workflows = []
    pr_workflows = []
    schedule_workflows = []

    for filename, info in workflows.items():
        triggers = info["triggers"]
        if "push" in triggers:
            push_workflows.append((filename, triggers["push"]))
        if "pull_request" in triggers:
            pr_workflows.append((filename, triggers["pull_request"]))
        if "schedule" in triggers:
            schedule_workflows.append((filename, triggers["schedule"]))

    print(f"📤 Push-triggered workflows: {len(push_workflows)}")
    for wf, config in push_workflows:
        branches = config.get("branches", ["all"])
        paths = config.get("paths", ["all"])
        print(f"   {wf}: branches={branches}, paths={paths}")

    print(f"\n📥 PR-triggered workflows: {len(pr_workflows)}")
    for wf, config in pr_workflows:
        branches = config.get("branches", ["all"])
        paths = config.get("paths", ["all"])
        print(f"   {wf}: branches={branches}, paths={paths}")

    print(f"\n⏰ Scheduled workflows: {len(schedule_workflows)}")
    for wf, config in schedule_workflows:
        print(f"   {wf}: {config}")

    # Validate dependencies and quality gates
    print("\n=== QUALITY GATE VALIDATION ===\n")

    quality_gates_file = None
    for filename, info in workflows.items():
        if "quality" in info["name"].lower() and "gate" in info["name"].lower():
            quality_gates_file = filename
            break

    if quality_gates_file:
        print(f"✅ Quality Gates workflow found: {quality_gates_file}")

        # Check if quality gates workflow waits for other workflows
        with open(f".github/workflows/{quality_gates_file}", "r") as f:
            content = yaml.safe_load(f)

        workflow_run_triggers = content.get(
            "workflow_run", content.get(True, {}).get("workflow_run", {})
        )
        if workflow_run_triggers:
            required_workflows = workflow_run_triggers.get("workflows", [])
            print(f"   Waits for workflows: {required_workflows}")
        else:
            print("   ⚠️ No workflow_run triggers found")
    else:
        print("❌ No Quality Gates workflow found")

    # Check security scanning
    security_workflows = [
        wf for wf in workflows if "security" in workflows[wf]["name"].lower()
    ]
    if security_workflows:
        print(f"✅ Security workflows found: {', '.join(security_workflows)}")
    else:
        print("❌ No security workflows found")

    # Check coverage analysis
    coverage_workflows = [
        wf for wf in workflows if "coverage" in workflows[wf]["name"].lower()
    ]
    if coverage_workflows:
        print(f"✅ Coverage workflows found: {', '.join(coverage_workflows)}")
    else:
        print("❌ No coverage workflows found")

    return workflows


if __name__ == "__main__":
    analyze_workflows()
