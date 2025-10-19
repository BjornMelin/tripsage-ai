# TripSage AI CI/CD Architecture (Simplified)

## Overview

This document describes the comprehensive CI/CD pipeline architecture for TripSage AI, designed with security, performance, and maintainability as core principles.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Validation Report](#validation-report)
- [Workflow Structure](#workflow-structure)
- [Security Implementation](#security-implementation)
- [Performance Optimizations](#performance-optimizations)
- [Required Secrets](#required-secrets)
- [Maintenance Guide](#maintenance-guide)

## Architecture Overview

The CI/CD system is built around two main workflows:

1. **CI** (`ci.yml`) - Minimal testing and quality checks for backend and frontend
2. **Weekly Security** (`security.yml`) - Scheduled (and manual) secrets scan

### Key Design Principles

1. **KISS/DRY/YAGNI**: Small workflows, no custom composite actions
2. **Path Filtering**: Each job runs only when relevant areas change
3. **Fast Feedback**: No matrices or redundant gates; clear summaries
4. **Security**: GH secret scanning config plus weekly gitleaks

## Validation Report

### ✅ Files in scope

- `.github/workflows/ci.yml`
- `.github/workflows/security.yml`
- `.github/secret_scanning.yml`

### ✅ Action Usage

Use supported major tags for official actions (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4`). Avoid bespoke composite actions unless shared cross-repo.

### ✅ Path References

All path references are correctly structured:

- Backend paths: `tripsage/`, `tripsage_core/`, `scripts/`, `tests/`
- Frontend paths: `frontend/` with proper working directory settings
- Migration paths: `supabase/migrations/`, `scripts/database/`
- GitHub paths: `.github/workflows/`, `.github/actions/`

### Notes

- Backend pyright/unit tests are temporarily soft-fail while stabilizing. We will make them blocking after consecutive green runs on `main`.

## Workflow Structure

### CI Workflow

Two jobs run in parallel: Backend (lint/type/unit) and Frontend (lint/type/unit). Each is path-scoped and minimal. The workflow triggers when backend code, tests, dependency manifests/locks, frontend files, or CI configs change, including:

`tripsage/**`, `tripsage_core/**`, `scripts/**`, `supabase/**`, `tests/**`, `requirements*.txt`, `requirements/**`, `uv.lock`, `poetry.lock`, `pyproject.toml`, `ruff.toml`, `pyrightconfig.json`, `setup.cfg`, `pytest.ini`, `frontend/**`, `.github/workflows/**`.

### Key Features

1. **Path Filtering**: The `changes` job analyzes which files changed to skip unnecessary jobs
2. **Matrix Testing**: Tests run across multiple Python versions (3.11, 3.12, 3.13) and OS (Ubuntu, Windows, macOS)
3. **Service Containers**: PostgreSQL and DragonflyDB run as service containers for integration tests
4. **Coverage Tracking**: Automatic coverage reporting with Codecov integration
5. **Security Scanning**: Multiple security tools (Bandit, Safety, Trivy) run in parallel

## Security Implementation

### 1. Secrets Scanning

Use weekly `security.yml` with gitleaks; maintain `.github/secret_scanning.yml` `paths-ignore` for example env templates.

### 2. RLS Policy Validation

```yaml
- name: RLS Security Checks
  run: |
    tables=("trips" "memories" "flights" "accommodations" "notifications")
    for table in "${tables[@]}"; do
      if grep -q "CREATE POLICY.*ON $table" supabase/migrations/*.sql; then
        echo "✅ RLS policies found for $table"
      fi
    done
```

### 3. Dependency Scanning

- Bandit for Python static analysis
- Safety for known vulnerabilities
- Trivy for container scanning
- npm/pnpm audit for frontend dependencies

### 4. SARIF Upload

Security findings are uploaded to GitHub Security tab for centralized tracking.

## Performance Optimizations

### 1. Intelligent Caching

**Python/uv caching**:

```yaml
key: ${{ runner.os }}-uv-${{ matrix.python-version }}-${{ hashFiles('**/requirements*.txt', '**/pyproject.toml') }}
```

**Node/pnpm caching**:

```yaml
key: ${{ runner.os }}-pnpm-${{ inputs.node-version }}-${{ hashFiles('frontend/pnpm-lock.yaml') }}
```

**Next.js build caching**:

```yaml
path: ./frontend/.next/cache
key: ${{ runner.os }}-nextjs-${{ matrix.build-mode }}-${{ hashFiles('frontend/pnpm-lock.yaml') }}
```

### 2. Parallel Execution

- Backend and frontend jobs run in parallel
- Matrix strategy for multi-version testing
- Concurrent security scans

### 3. Retry Logic

```yaml
for i in {1..${{ env.MAX_RETRIES }}}; do
  if pytest tests/unit/; then
    break
  elif [ $i -eq ${{ env.MAX_RETRIES }} ]; then
    exit 1
  fi
  sleep ${{ env.RETRY_DELAY }}
done
```

## Required Secrets

The following secrets must be configured in GitHub repository settings:

### Essential Secrets

- `CODECOV_TOKEN` - For coverage reporting
- `SLACK_WEBHOOK_URL` - For CI notifications (optional)

### Deployment Secrets (Environment-specific)

- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Supabase anonymous key
- `SUPABASE_SERVICE_KEY` - Supabase service role key
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic API key
- `DUFFEL_API_KEY` - Duffel API key
- `GOOGLE_MAPS_API_KEY` - Google Maps API key
- `DRAGONFLY_PASSWORD` - DragonflyDB password (if used)

### AWS Deployment (if using AWS)

- `AWS_ACCOUNT_ID` - AWS account ID for OIDC
- `AWS_REGION` - AWS region
- `AWS_ROLE_NAME` - IAM role for deployment

## Maintenance Guide

### Adding New Tests

1. Unit tests go in `tests/unit/`
2. Integration tests go in `tests/integration/`
3. Performance tests go in `tests/performance/`
4. E2E tests go in `frontend/tests/e2e/`

### Updating Dependencies

1. Python: Update `requirements*.txt` or `pyproject.toml`
2. Node: Update `frontend/package.json` and run `pnpm install`
3. Actions: Update SHA in workflows and `action.yml` files

### Coverage Thresholds

Configured in environment variables:

- Backend: `BACKEND_COVERAGE_THRESHOLD=85`
- Frontend: `FRONTEND_COVERAGE_THRESHOLD=80`

### Monitoring CI Performance

1. Check workflow run times in Actions tab
2. Monitor cache hit rates
3. Review artifact sizes
4. Track flaky test patterns

### Common Issues

1. **Cache misses**: Check if dependency files changed
2. **Flaky tests**: Increase retry count or timeout
3. **Service container failures**: Check health check configuration
4. **Windows-specific failures**: Ensure cross-platform compatibility

## Best Practices

1. **Always pin actions** to commit SHAs, not tags
2. **Use path filtering** to avoid unnecessary job runs
3. **Implement retry logic** for network-dependent tests
4. **Cache aggressively** but invalidate appropriately
5. **Run security scans** on every PR
6. **Keep secrets minimal** and rotate regularly
7. **Monitor performance** and optimize bottlenecks
8. **Document changes** to CI configuration

## Utilities Workflow Features

The utilities workflow provides several automation features:

1. **PR Validation**: Checks conventional commits, PR description quality
2. **Auto-labeling**: Labels PRs based on files changed
3. **Breaking Change Detection**: Identifies potential breaking changes
4. **Merge Conflict Detection**: Alerts on conflicts
5. **Code Quality Summary**: Provides metrics on PR changes
6. **Auto-assign Reviewers**: Based on CODEOWNERS
7. **Stale Management**: Marks and closes stale issues/PRs
8. **Release Automation**: Generates release notes
9. **PR Metrics**: Monthly metrics reports

## Conclusion

This CI/CD architecture provides a robust, secure, and performant foundation for TripSage AI development. The system is designed to catch issues early, provide fast feedback, and maintain high code quality standards while optimizing for developer experience.

For questions or improvements, please open an issue or contact the maintainers.
