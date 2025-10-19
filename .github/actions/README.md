# GitHub Composite Actions

This directory contains reusable composite actions for the TripSage project.

## Available Actions

### setup-python

Sets up Python environment with uv package manager, caching, and dependency installation.

**Usage:**
```yaml
- uses: ./.github/actions/setup-python
  with:
    python-version: '3.13'
    install-dependencies: true
```

**Inputs:**
- `python-version`: Python version to use (default: '3.13')
- `cache-dependency-path`: Path to dependency files for caching (default: 'pyproject.toml')
- `create-venv`: Whether to create a virtual environment (default: 'true')
- `venv-path`: Path for the virtual environment (default: '.venv')
- `install-dependencies`: Whether to install dependencies (default: 'true')
- `uv-version`: Version of uv to install (default: 'latest')

### setup-node

Sets up Node.js environment with pnpm package manager and intelligent caching.

**Usage:**
```yaml
- uses: ./.github/actions/setup-node
  with:
    node-version: '20'
    pnpm-version: '9'
    working-directory: 'frontend'
```

**Inputs:**
- `node-version`: Node.js version to use (default: '20')
- `pnpm-version`: pnpm version to use (default: '9')
- `working-directory`: Working directory for Node.js operations (default: 'frontend')
- `install-dependencies`: Whether to install dependencies (default: 'true')
- `cache-dependency-path`: Path to pnpm-lock.yaml for caching (default: 'frontend/pnpm-lock.yaml')

### security-scan

Unified security scanning for Python and Node.js code, including dependency vulnerabilities and hardcoded secrets.

**Usage:**
```yaml
- uses: ./.github/actions/security-scan
  with:
    scan-python: true
    scan-frontend: true
    fail-on-severity: 'high'
```

**Inputs:**
- `scan-python`: Whether to scan Python code (default: 'true')
- `scan-frontend`: Whether to scan frontend/Node.js code (default: 'true')
- `python-path`: Path to Python code (default: '.')
- `frontend-path`: Path to frontend code (default: 'frontend')
- `fail-on-severity`: Minimum severity to fail the scan (default: 'high')
- `create-issues`: Whether to create GitHub issues for findings (default: 'false')
- `upload-sarif`: Whether to upload SARIF results to GitHub Security (default: 'true')

## Example Workflow

```yaml
name: CI
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # Setup Python environment
      - uses: ./.github/actions/setup-python
        with:
          python-version: '3.13'
      
      # Setup Node environment
      - uses: ./.github/actions/setup-node
        with:
          working-directory: 'frontend'
      
      # Run security scans
      - uses: ./.github/actions/security-scan
        with:
          fail-on-severity: 'medium'
      
      # Run tests
      - run: uv run pytest
      - run: pnpm test
        working-directory: frontend
```

## Version Pinning

All external actions are pinned to specific commit SHAs for security and reproducibility unless GitHub requires a supported major tag:
- `actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2b` (v5.3.0)
- `actions/setup-node@39370e3970a6d050c480ffad4ff0ed4d3fdee5af` (v4.1.0)
- `pnpm/action-setup@fe02b34f77f8bc703788d5817da081398fad5dd2` (v4.0.0)
- `actions/cache@v4` (GitHub requires supported major tag)
- `actions/upload-artifact@6f51ac03b9356f520e9adb1b1b7802705f340c2b` (v4.5.0)
