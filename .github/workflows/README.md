# GitHub Workflows

This directory contains the CI/CD pipeline configuration for TripSage. The workflows are designed to ensure code quality, security, and maintainability through automated testing and validation.

## Workflow Overview

| Workflow | Purpose | Triggers | Duration |
|----------|---------|----------|----------|
| [`backend-ci.yml`](./backend-ci.yml) | Python backend validation | Push, PR | ~6 min |
| [`frontend-ci-simple.yml`](./frontend-ci-simple.yml) | Frontend validation | Push, PR | ~8 min |
| [`security.yml`](./security.yml) | Security vulnerability scanning | Push, PR, Schedule | ~12 min |
| [`coverage.yml`](./coverage.yml) | Code coverage analysis | Push, PR, Schedule | ~15 min |
| [`pr-automation.yml`](./pr-automation.yml) | PR quality checks | PR events | ~2 min |
| [`quality-gates.yml`](./quality-gates.yml) | Final quality validation | PR, Push | ~3 min |

## Quick Start

### For Developers

When you create a PR, the following happens automatically:

1. **PR Automation** runs immediately:
   - Auto-labels based on changed files
   - Validates PR title format
   - Checks description length
   - Detects breaking changes

2. **Core CI Workflows** run in parallel:
   - Backend CI (Python tests, linting, build)
   - Frontend CI (TypeScript tests, linting, build)
   - Security scanning (vulnerability detection)
   - Coverage analysis (test coverage validation)

3. **Quality Gates** validates all results:
   - Ensures all CI checks pass
   - Enforces coverage thresholds
   - Blocks merge if quality standards not met

### Quality Requirements

Your PR must meet these requirements to be merged:

- ✅ **Backend Coverage**: ≥85%
- ✅ **Frontend Coverage**: ≥80%
- ✅ **All Tests Pass**: 100% pass rate
- ✅ **No Critical Security Issues**: Zero critical vulnerabilities
- ✅ **Clean Code**: Pass all linting and formatting checks
- ✅ **Successful Build**: Backend and frontend must build successfully

## Common Commands

```bash
# Run backend tests locally
uv run pytest --cov=tripsage --cov=tripsage_core

# Run frontend tests locally
cd frontend && pnpm test

# Fix code formatting
ruff format . && cd frontend && pnpm format

# Check for security issues
bandit -r tripsage/ tripsage_core/
cd frontend && pnpm audit
```

## Troubleshooting

### My PR is failing CI

1. **Check the failed workflow**: Click on the red ❌ next to the failed check
2. **Read the error logs**: Look for specific error messages
3. **Fix locally**: Reproduce and fix the issue locally
4. **Push changes**: CI will re-run automatically

### Common Fixes

**Backend linting errors**:

```bash
ruff check . --fix
ruff format .
```

**Frontend type errors**:

```bash
cd frontend
pnpm type-check
# Fix TypeScript errors in your code
```

**Test failures**:

```bash
# Run specific test
uv run pytest tests/path/to/test.py::test_name -v
```

**Coverage too low**:

- Add tests for uncovered code
- Remove dead code that can't be tested

## Security

The security workflow automatically scans for:

- Exposed secrets and API keys
- Vulnerable dependencies
- Code security patterns
- Docker security issues

**Never commit real secrets!** Use environment variables and `.env.example` files.

## Getting Help

1. **Read the full documentation**:
   - [Repository Setup Guide](../REPOSITORY_SETUP.md) - Complete setup instructions
   - [Branch Conventions](../BRANCH_CONVENTIONS.md) - Branch naming and workflow triggers
2. **Check existing issues**: Search for similar problems
3. **Ask the team**: Contact maintainers for help

## Workflow Maintenance

### Adding New Workflows

1. Create new `.yml` file in this directory
2. Follow existing patterns for structure
3. Add appropriate triggers and permissions
4. Test on feature branch before merging
5. Update this README

### Modifying Existing Workflows

1. Make changes in feature branch
2. Test thoroughly before merging to main
3. Monitor workflow runs after merge
4. Update documentation as needed

### Performance Optimization

- Use caching for dependencies
- Run jobs in parallel where possible
- Set appropriate timeouts
- Use specific runner types for workloads

## Status Badges

Add these to your PR descriptions to show CI status:

```markdown
![Backend CI](https://github.com/BjornMelin/TripSage/workflows/Backend%20CI/badge.svg)
![Frontend CI](https://github.com/BjornMelin/TripSage/workflows/Frontend%20CI/badge.svg)
![Security](https://github.com/BjornMelin/TripSage/workflows/Security%20Scanning/badge.svg)
```

## Best Practices

1. **Keep workflows fast**: Optimize for quick feedback
2. **Fail fast**: Catch issues early in the pipeline
3. **Clear naming**: Use descriptive job and step names
4. **Proper caching**: Cache dependencies and build artifacts
5. **Security first**: Never expose secrets in logs
6. **Documentation**: Keep this README updated

---

For detailed information about each workflow, troubleshooting, and advanced configuration, see the [complete CI documentation](../CI_PIPELINE_DOCUMENTATION.md).
