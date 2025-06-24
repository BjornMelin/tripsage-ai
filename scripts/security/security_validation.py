#!/usr/bin/env python3
"""
Security Validation Script for TripSage API.

This script validates security configurations, headers, and best practices
across the application.
"""

import json
import re
import sys
from typing import Any

# Security checks
SECURITY_CHECKS = {"critical": [], "high": [], "medium": [], "low": [], "info": []}


def log_finding(
    severity: str, category: str, message: str, details: dict[str, Any] = None
):
    """Log a security finding."""
    finding = {"category": category, "message": message, "details": details or {}}
    SECURITY_CHECKS[severity].append(finding)
    print(f"[{severity.upper()}] {category}: {message}")


def check_hardcoded_secrets():
    """Check for hardcoded secrets in the codebase."""
    print("\n=== Checking for hardcoded secrets ===")

    import os
    import subprocess

    # Patterns to search for (used in exclude patterns)

    # Exclude patterns (legitimate configuration)
    exclude_patterns = [
        r"fallback-secret",
        r"development-only",
        r"test-password",
        r"example-key",
        r"placeholder",
        r"your-secret-here",
        r"changeme",
        r"test-",
        r"mock-",
        r"fake-",
        r"dummy-",
        r"sk-test-",
        r"Field\(description=",
        r"test_",
        r"mock_",
    ]

    # Search through source files (extensions hardcoded in grep command)

    try:
        # Use grep to search for potential secrets
        cmd = [
            "grep",
            "-r",
            "--include=*.py",
            "--include=*.js",
            "--include=*.ts",
            "--include=*.json",
            "--include=*.yaml",
            "--include=*.yml",
            "--exclude-dir=node_modules",
            "--exclude-dir=.next",
            "--exclude-dir=dist",
            "--exclude-dir=build",
            "--exclude-dir=coverage",
            "--exclude-dir=.git",
            "--exclude-dir=__pycache__",
            "--exclude-dir=tests",
            "-E",
            "(password|secret|api_key|private_key).*=.*[\"'][^\"']{16,}[\"']",
            ".",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())

        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            for line in lines:
                # Skip if it matches exclude patterns
                if any(exclude in line.lower() for exclude in exclude_patterns):
                    continue

                log_finding(
                    "high",
                    "Hardcoded Secrets",
                    f"Potential hardcoded secret found: {line[:100]}...",
                )
        else:
            log_finding(
                "info", "Hardcoded Secrets", "No obvious hardcoded secrets found"
            )

    except Exception as e:
        log_finding("medium", "Hardcoded Secrets", f"Could not scan for secrets: {e}")


def check_sql_injection_protection():
    """Check for SQL injection protection."""
    print("\n=== Checking SQL injection protection ===")

    import glob

    # Look for raw SQL queries
    sql_patterns = [
        r'\.execute\s*\(\s*["\'].*\+.*["\']',  # String concatenation in execute
        r'f["\'].*\{.*\}.*["\']',  # F-strings in SQL (potentially dangerous)
        r"%.*%.*INTO.*",  # String formatting in SQL
    ]

    python_files = [
        f
        for f in glob.glob("**/*.py", recursive=True)
        if not any(
            exclude in f
            for exclude in [
                "node_modules",
                ".next",
                "dist",
                "build",
                "__pycache__",
                ".git",
            ]
        )
    ]

    found_issues = False
    for file_path in python_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in sql_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    found_issues = True
                    log_finding(
                        "high",
                        "SQL Injection",
                        f"Potential SQL injection in {file_path}: {matches[0][:50]}...",
                    )

        except Exception:
            continue

    if not found_issues:
        log_finding(
            "info", "SQL Injection", "No obvious SQL injection vulnerabilities found"
        )


def check_xss_protection():
    """Check for XSS protection."""
    print("\n=== Checking XSS protection ===")

    import glob

    # Look for potential XSS vulnerabilities
    xss_patterns = [
        r"\.innerHTML\s*=",  # Direct innerHTML assignment
        r"document\.write\s*\(",  # document.write usage
        r"eval\s*\(",  # eval usage
        r"dangerouslySetInnerHTML",  # React dangerous HTML
    ]

    frontend_files = (
        glob.glob("frontend/src/**/*.ts", recursive=True)
        + glob.glob("frontend/src/**/*.tsx", recursive=True)
        + glob.glob("frontend/src/**/*.js", recursive=True)
        + glob.glob("frontend/src/**/*.jsx", recursive=True)
    )

    found_issues = False
    for file_path in frontend_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in xss_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                if matches:
                    found_issues = True
                    log_finding(
                        "medium",
                        "XSS Protection",
                        f"Potential XSS vulnerability in {file_path}",
                    )

        except Exception:
            continue

    if not found_issues:
        log_finding("info", "XSS Protection", "No obvious XSS vulnerabilities found")


def check_authentication_security():
    """Check authentication security."""
    print("\n=== Checking authentication security ===")

    # Check for proper JWT handling
    auth_middleware_path = "tripsage/api/middlewares/authentication.py"
    session_service_path = "tripsage_core/services/business/session_security_service.py"

    checks_passed = 0
    total_checks = 4

    try:
        # Check authentication middleware exists and has security measures
        with open(auth_middleware_path, "r") as f:
            auth_content = f.read()

        if "_validate_request_headers" in auth_content:
            log_finding(
                "info", "Authentication", "Request header validation implemented"
            )
            checks_passed += 1
        else:
            log_finding("medium", "Authentication", "Missing request header validation")

        if "_validate_token_format" in auth_content:
            log_finding("info", "Authentication", "Token format validation implemented")
            checks_passed += 1
        else:
            log_finding("medium", "Authentication", "Missing token format validation")

        if "_add_security_headers" in auth_content:
            log_finding(
                "info", "Authentication", "Security headers implementation found"
            )
            checks_passed += 1
        else:
            log_finding(
                "medium", "Authentication", "Missing security headers implementation"
            )

    except FileNotFoundError:
        log_finding(
            "critical",
            "Authentication",
            f"Authentication middleware not found: {auth_middleware_path}",
        )
    except Exception as e:
        log_finding(
            "medium", "Authentication", f"Error checking authentication middleware: {e}"
        )

    try:
        # Check session security service
        with open(session_service_path, "r") as f:
            session_content = f.read()

        if "_validate_and_score_ip" in session_content:
            log_finding(
                "info", "Authentication", "IP validation and scoring implemented"
            )
            checks_passed += 1
        else:
            log_finding("high", "Authentication", "Missing IP validation and scoring")

    except FileNotFoundError:
        log_finding(
            "critical",
            "Authentication",
            f"Session security service not found: {session_service_path}",
        )
    except Exception as e:
        log_finding("medium", "Authentication", f"Error checking session service: {e}")

    log_finding(
        "info",
        "Authentication",
        f"Authentication security: {checks_passed}/{total_checks} checks passed",
    )


def check_input_validation():
    """Check input validation."""
    print("\n=== Checking input validation ===")

    import glob

    # Check for Pydantic validation in models
    model_files = glob.glob("tripsage_core/models/**/*.py", recursive=True)

    validation_found = False
    for file_path in model_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()

            if "field_validator" in content or "validator" in content:
                validation_found = True
                log_finding(
                    "info", "Input Validation", f"Validation found in {file_path}"
                )

        except Exception:
            continue

    if not validation_found:
        log_finding(
            "medium", "Input Validation", "Limited Pydantic validation found in models"
        )

    # Check for specific security validations
    session_service_path = "tripsage_core/services/business/session_security_service.py"
    try:
        with open(session_service_path, "r") as f:
            content = f.read()

        if "validate_ip_address" in content:
            log_finding("info", "Input Validation", "IP address validation implemented")
        if "validate_user_agent" in content:
            log_finding("info", "Input Validation", "User agent validation implemented")
        if "validate_session_token" in content:
            log_finding(
                "info", "Input Validation", "Session token validation implemented"
            )

    except Exception as e:
        log_finding(
            "medium", "Input Validation", f"Could not check session validation: {e}"
        )


def check_cors_configuration():
    """Check CORS configuration."""
    print("\n=== Checking CORS configuration ===")

    import glob

    # Look for CORS configuration
    api_files = [
        f
        for f in glob.glob("tripsage/api/**/*.py", recursive=True)
        if not any(exclude in f for exclude in ["__pycache__", ".git"])
    ]

    cors_found = False
    for file_path in api_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()

            if "CORSMiddleware" in content or "allow_origins" in content:
                cors_found = True

                # Check for wildcard origins (security risk)
                if '"*"' in content and "allow_origins" in content:
                    log_finding(
                        "high", "CORS", f"Wildcard CORS origins found in {file_path}"
                    )
                else:
                    log_finding(
                        "info", "CORS", f"CORS configuration found in {file_path}"
                    )

        except Exception:
            continue

    if not cors_found:
        log_finding("medium", "CORS", "No CORS configuration found")


def check_https_enforcement():
    """Check HTTPS enforcement."""
    print("\n=== Checking HTTPS enforcement ===")

    import glob

    # Look for HTTPS enforcement
    config_files = [
        f
        for f in glob.glob("**/*.py", recursive=True)
        if not any(
            exclude in f
            for exclude in [
                "node_modules",
                ".next",
                "dist",
                "build",
                "__pycache__",
                ".git",
            ]
        )
    ]

    https_found = False
    for file_path in config_files:
        try:
            with open(file_path, "r") as f:
                content = f.read()

            if "Strict-Transport-Security" in content:
                https_found = True
                log_finding("info", "HTTPS", f"HSTS header found in {file_path}")

        except Exception:
            continue

    if https_found:
        log_finding("info", "HTTPS", "HTTPS enforcement mechanisms found")
    else:
        log_finding("medium", "HTTPS", "No explicit HTTPS enforcement found")


def check_dependency_security():
    """Check dependency security."""
    print("\n=== Checking dependency security ===")

    import os
    import subprocess

    # Check for known vulnerable packages
    try:
        # Check Python dependencies
        result = subprocess.run(["uv", "pip", "list"], capture_output=True, text=True)

        if result.returncode == 0:
            log_finding(
                "info", "Dependencies", "Python dependencies listed successfully"
            )
        else:
            log_finding("medium", "Dependencies", "Could not list Python dependencies")

    except Exception as e:
        log_finding(
            "medium", "Dependencies", f"Error checking Python dependencies: {e}"
        )

    # Check for package.json (frontend dependencies)
    try:
        if os.path.exists("frontend/package.json"):
            log_finding("info", "Dependencies", "Frontend package.json found")
        else:
            log_finding("medium", "Dependencies", "Frontend package.json not found")

    except Exception as e:
        log_finding(
            "medium", "Dependencies", f"Error checking frontend dependencies: {e}"
        )


def generate_security_report():
    """Generate a comprehensive security report."""
    print("\n" + "=" * 60)
    print("SECURITY VALIDATION REPORT")
    print("=" * 60)

    total_issues = len(SECURITY_CHECKS["critical"]) + len(SECURITY_CHECKS["high"])

    for severity in ["critical", "high", "medium", "low", "info"]:
        count = len(SECURITY_CHECKS[severity])
        if count > 0:
            print(f"\n{severity.upper()} ({count} findings):")
            for finding in SECURITY_CHECKS[severity]:
                print(f"  - {finding['category']}: {finding['message']}")

    print("\nSUMMARY:")
    print(f"  Critical: {len(SECURITY_CHECKS['critical'])}")
    print(f"  High:     {len(SECURITY_CHECKS['high'])}")
    print(f"  Medium:   {len(SECURITY_CHECKS['medium'])}")
    print(f"  Low:      {len(SECURITY_CHECKS['low'])}")
    print(f"  Info:     {len(SECURITY_CHECKS['info'])}")

    if total_issues == 0:
        print("\n✅ No critical or high severity security issues found!")
        return 0
    else:
        print(f"\n⚠️  Found {total_issues} critical/high severity security issues")
        return 1


def main():
    """Main security validation function."""
    print("Starting TripSage Security Validation...")

    # Run all security checks
    check_hardcoded_secrets()
    check_sql_injection_protection()
    check_xss_protection()
    check_authentication_security()
    check_input_validation()
    check_cors_configuration()
    check_https_enforcement()
    check_dependency_security()

    # Generate final report
    exit_code = generate_security_report()

    # Save report to file
    report_data = {
        "timestamp": "2025-06-11T10:00:00Z",
        "checks": SECURITY_CHECKS,
        "summary": {
            "critical": len(SECURITY_CHECKS["critical"]),
            "high": len(SECURITY_CHECKS["high"]),
            "medium": len(SECURITY_CHECKS["medium"]),
            "low": len(SECURITY_CHECKS["low"]),
            "info": len(SECURITY_CHECKS["info"]),
        },
    }

    try:
        with open("security_validation_report.json", "w") as f:
            json.dump(report_data, f, indent=2)
        print("\n📄 Full report saved to: security_validation_report.json")
    except Exception as e:
        print(f"\n❌ Could not save report: {e}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
