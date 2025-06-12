#!/usr/bin/env python3
"""
CI Pipeline Validation Report Generator
"""
import yaml
import os
import json
from datetime import datetime

def generate_validation_report():
    print("🔍 CI/CD Pipeline Validation Report")
    print("=" * 50)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Repository: TripSage AI")
    print()

    # Track validation results
    validation_results = {
        "syntax_validation": [],
        "trigger_validation": [],
        "dependency_validation": [],
        "security_validation": [],
        "quality_gate_validation": [],
        "secrets_validation": []
    }

    workflow_dir = ".github/workflows"
    workflows = {}

    # 1. SYNTAX VALIDATION
    print("📝 1. Workflow Syntax Validation")
    print("-" * 30)
    
    for filename in os.listdir(workflow_dir):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            try:
                with open(f"{workflow_dir}/{filename}", 'r') as f:
                    content = yaml.safe_load(f)
                    triggers = content.get('on', content.get(True, {}))
                    workflows[filename] = {
                        'name': content.get('name', 'Unnamed'),
                        'triggers': triggers,
                        'jobs': list(content.get('jobs', {}).keys()),
                        'permissions': content.get('permissions', {}),
                        'env': content.get('env', {}),
                        'services_used': []
                    }
                    
                    # Check for services in jobs
                    for job_name, job_config in content.get('jobs', {}).items():
                        if 'services' in job_config:
                            workflows[filename]['services_used'].extend(job_config['services'].keys())
                    
                print(f"✅ {filename} - Valid YAML syntax")
                validation_results["syntax_validation"].append({"file": filename, "status": "pass", "message": "Valid YAML"})
                
            except yaml.YAMLError as e:
                print(f"❌ {filename} - YAML syntax error: {e}")
                validation_results["syntax_validation"].append({"file": filename, "status": "fail", "message": f"YAML error: {e}"})
            except Exception as e:
                print(f"❌ {filename} - Error: {e}")
                validation_results["syntax_validation"].append({"file": filename, "status": "fail", "message": f"Error: {e}"})

    # 2. TRIGGER VALIDATION
    print("\n🎯 2. Trigger Pattern Validation")
    print("-" * 30)
    
    trigger_issues = []
    
    # Check for conflicting branch patterns
    backend_branches = set()
    frontend_branches = set()
    
    for filename, info in workflows.items():
        triggers = info['triggers']
        if 'push' in triggers:
            branches = triggers['push'].get('branches', [])
            if 'backend' in filename.lower():
                backend_branches.update(branches)
            elif 'frontend' in filename.lower():
                frontend_branches.update(branches)
    
    # Check branch consistency
    if backend_branches != frontend_branches:
        trigger_issues.append("Backend and frontend CI have different branch triggers")
        print(f"⚠️  Branch trigger mismatch:")
        print(f"   Backend: {backend_branches}")
        print(f"   Frontend: {frontend_branches}")
    else:
        print("✅ Branch triggers are consistent across CI workflows")
    
    # Check for path filtering
    path_filtered_workflows = []
    for filename, info in workflows.items():
        triggers = info['triggers']
        if 'push' in triggers and 'paths' in triggers['push']:
            path_filtered_workflows.append(filename)
    
    print(f"✅ {len(path_filtered_workflows)} workflows use path filtering")
    for wf in path_filtered_workflows:
        print(f"   - {wf}")
    
    validation_results["trigger_validation"] = trigger_issues

    # 3. DEPENDENCY VALIDATION
    print("\n🔗 3. Workflow Dependencies")
    print("-" * 30)
    
    quality_gates_workflow = None
    dependent_workflows = []
    
    for filename, info in workflows.items():
        if 'quality' in info['name'].lower() and 'gate' in info['name'].lower():
            quality_gates_workflow = filename
            triggers = info['triggers']
            if 'workflow_run' in triggers:
                dependent_workflows = triggers['workflow_run'].get('workflows', [])
    
    if quality_gates_workflow:
        print(f"✅ Quality Gates workflow found: {quality_gates_workflow}")
        if dependent_workflows:
            print(f"   Depends on: {', '.join(dependent_workflows)}")
            validation_results["dependency_validation"].append({"status": "pass", "message": f"Quality gates depend on {len(dependent_workflows)} workflows"})
        else:
            print("   ⚠️ No workflow dependencies found")
            validation_results["dependency_validation"].append({"status": "warning", "message": "No workflow dependencies configured"})
    else:
        print("❌ No Quality Gates workflow found")
        validation_results["dependency_validation"].append({"status": "fail", "message": "No quality gates workflow"})

    # 4. SECURITY VALIDATION
    print("\n🔒 4. Security Configuration")
    print("-" * 30)
    
    security_workflows = []
    security_scans = []
    
    for filename, info in workflows.items():
        if 'security' in info['name'].lower():
            security_workflows.append(filename)
            
            # Check for security scan jobs
            for job in info['jobs']:
                if any(keyword in job.lower() for keyword in ['secret', 'vulnerability', 'audit', 'scan']):
                    security_scans.append(f"{filename}:{job}")
    
    if security_workflows:
        print(f"✅ {len(security_workflows)} security workflows found")
        for wf in security_workflows:
            print(f"   - {wf}")
        
        print(f"✅ {len(security_scans)} security scan jobs found")
        for scan in security_scans:
            print(f"   - {scan}")
        
        validation_results["security_validation"].append({"status": "pass", "message": f"{len(security_workflows)} security workflows, {len(security_scans)} scan jobs"})
    else:
        print("❌ No security workflows found")
        validation_results["security_validation"].append({"status": "fail", "message": "No security workflows"})

    # 5. QUALITY GATES VALIDATION
    print("\n✅ 5. Quality Gates Configuration")
    print("-" * 30)
    
    coverage_thresholds = {}
    quality_checks = []
    
    for filename, info in workflows.items():
        env_vars = info.get('env', {})
        
        # Check for coverage thresholds
        for key, value in env_vars.items():
            if 'COVERAGE_THRESHOLD' in key:
                coverage_thresholds[key] = value
        
        # Check for quality-related jobs
        for job in info['jobs']:
            if any(keyword in job.lower() for keyword in ['quality', 'lint', 'test', 'coverage']):
                quality_checks.append(f"{filename}:{job}")
    
    if coverage_thresholds:
        print("✅ Coverage thresholds configured:")
        for threshold, value in coverage_thresholds.items():
            print(f"   - {threshold}: {value}%")
    else:
        print("⚠️ No coverage thresholds found in workflow env vars")
    
    print(f"✅ {len(quality_checks)} quality check jobs found")
    
    validation_results["quality_gate_validation"] = coverage_thresholds

    # 6. SECRETS VALIDATION
    print("\n🔐 6. Required Secrets")
    print("-" * 30)
    
    required_secrets = set()
    
    # Scan all workflow files for secret references
    for filename in os.listdir(workflow_dir):
        if filename.endswith('.yml') or filename.endswith('.yaml'):
            with open(f"{workflow_dir}/{filename}", 'r') as f:
                content = f.read()
                # Find all secret references
                import re
                secrets_found = re.findall(r'\$\{\{\s*secrets\.([A-Z_]+)\s*\}\}', content)
                required_secrets.update(secrets_found)
    
    if required_secrets:
        print("📋 Required repository secrets:")
        for secret in sorted(required_secrets):
            print(f"   - {secret}")
    else:
        print("ℹ️ No secrets required")
    
    validation_results["secrets_validation"] = list(required_secrets)

    # SUMMARY
    print("\n📊 VALIDATION SUMMARY")
    print("=" * 50)
    
    syntax_passed = len([r for r in validation_results["syntax_validation"] if r["status"] == "pass"])
    syntax_total = len(validation_results["syntax_validation"])
    
    print(f"📝 Syntax Validation: {syntax_passed}/{syntax_total} workflows passed")
    
    if validation_results["trigger_validation"]:
        print(f"🎯 Trigger Issues: {len(validation_results['trigger_validation'])} found")
        for issue in validation_results["trigger_validation"]:
            print(f"   - {issue}")
    else:
        print("🎯 Trigger Validation: ✅ All triggers configured correctly")
    
    dependency_status = validation_results["dependency_validation"]
    if dependency_status and dependency_status[0]["status"] == "pass":
        print("🔗 Dependencies: ✅ Quality gates properly configured")
    else:
        print("🔗 Dependencies: ⚠️ Quality gates need attention")
    
    security_status = validation_results["security_validation"]
    if security_status and security_status[0]["status"] == "pass":
        print("🔒 Security: ✅ Security workflows configured")
    else:
        print("🔒 Security: ❌ Security workflows missing")
    
    if validation_results["quality_gate_validation"]:
        print("✅ Quality Gates: ✅ Coverage thresholds configured")
    else:
        print("✅ Quality Gates: ⚠️ Coverage thresholds need configuration")
    
    secrets_count = len(validation_results["secrets_validation"])
    print(f"🔐 Secrets: {secrets_count} required secrets identified")

    # RECOMMENDATIONS
    print("\n💡 RECOMMENDATIONS")
    print("=" * 50)
    
    recommendations = []
    
    if syntax_passed < syntax_total:
        recommendations.append("Fix YAML syntax errors in workflow files")
    
    if validation_results["trigger_validation"]:
        recommendations.append("Resolve trigger pattern conflicts")
    
    if not quality_gates_workflow:
        recommendations.append("Implement quality gates workflow")
    
    if not security_workflows:
        recommendations.append("Add security scanning workflows")
    
    if not coverage_thresholds:
        recommendations.append("Configure coverage thresholds in workflow env vars")
    
    if required_secrets:
        recommendations.append("Ensure all required secrets are configured in repository settings")
    
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
    else:
        print("🎉 All validations passed! CI/CD pipeline is properly configured.")

    # PRODUCTION READINESS SCORE
    print("\n🏆 PRODUCTION READINESS SCORE")
    print("=" * 50)
    
    total_checks = 6
    passed_checks = 0
    
    if syntax_passed == syntax_total:
        passed_checks += 1
    if not validation_results["trigger_validation"]:
        passed_checks += 1
    if quality_gates_workflow and dependent_workflows:
        passed_checks += 1
    if security_workflows:
        passed_checks += 1
    if coverage_thresholds:
        passed_checks += 1
    if required_secrets:  # Having secrets is good
        passed_checks += 1
    
    score = (passed_checks / total_checks) * 100
    
    if score >= 90:
        grade = "🥇 Excellent"
    elif score >= 75:
        grade = "🥈 Good"
    elif score >= 60:
        grade = "🥉 Fair"
    else:
        grade = "📈 Needs Improvement"
    
    print(f"Score: {score:.1f}/100 - {grade}")
    print(f"Checks passed: {passed_checks}/{total_checks}")

if __name__ == "__main__":
    generate_validation_report()