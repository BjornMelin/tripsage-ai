# TripSage CI/CD Architecture (2025)

## Overview

This directory contains the modern CI/CD pipeline for TripSage, following 2025 best practices for GitHub Actions. The architecture has been streamlined from 7 workflows to 3 main workflows with reusable components.

## Architecture

### Main Workflows

1. **`ci.yml`** - Unified Continuous Integration
   - Combines backend, frontend, and coverage checks
   - Path-based filtering for efficiency
   - Matrix testing across Python versions and OS
   - Integrated security scanning
   - Unified coverage reporting

2. **`deploy.yml`** - Production Deployment
   - OIDC authentication for AWS
   - Multi-environment support (staging, production)
   - Automatic rollback capabilities
   - Comprehensive smoke tests
   - GitHub Deployments API integration

3. **`utilities.yml`** - PR Automation & Maintenance
   - PR validation and auto-labeling
   - Breaking change detection
   - Stale issue/PR management
   - Release automation helpers
   - Developer experience improvements

### Composite Actions

Located in `.github/actions/`:

- **`setup-python`** - Python environment setup with uv
- **`setup-node`** - Node.js environment setup with pnpm
- **`security-scan`** - Unified security scanning

### Configuration Files

- **`dependabot.yml`** - Automated dependency updates with grouping
- **`CODEOWNERS`** - Code ownership for reviews
- **`ci-config.yml`** - Shared CI configuration values

## Key Features

### Security
- All actions pinned to commit SHAs
- OIDC authentication (no long-lived credentials)
- Integrated vulnerability scanning
- Secret scanning and hardcoded credential detection
- Minimal workflow permissions

### Performance
- Advanced multi-level caching
- Matrix builds with intelligent exclusions
- Parallel test execution
- Path filtering to run only necessary jobs
- Larger runners for resource-intensive tasks

### Reliability
- Smart retry mechanisms for flaky tests
- Proper health checks for services
- Timeout configurations
- Comprehensive error handling
- Rollback capabilities for failed deployments

### Developer Experience
- Clear error messages and logs
- Helpful PR automation
- Fast feedback loops
- Single source of truth for CI
- Reduced maintenance overhead

## Required Secrets

### GitHub Actions
- `CODECOV_TOKEN` - For coverage reporting

### AWS Deployment
- `AWS_DEPLOY_ROLE_ARN` - OIDC role for AWS
- `AWS_REGION` - AWS region (default: us-east-1)

### Supabase
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_ANON_KEY` - Public anonymous key
- `SUPABASE_SERVICE_KEY` - Service role key
- `SUPABASE_ACCESS_TOKEN` - CLI access token
- `SUPABASE_PROJECT_ID` - Project reference

### Vercel
- `VERCEL_TOKEN` - Vercel API token
- `VERCEL_ORG_ID` - Organization ID
- `VERCEL_PROJECT_ID` - Project ID

### Notifications (Optional)
- `SLACK_WEBHOOK_URL` - Slack deployment notifications

## Usage

### Running CI
CI runs automatically on:
- Push to main, develop, feat/*, session/* branches
- Pull requests to main or develop
- Manual workflow dispatch

### Manual Deployment
```bash
# Deploy to staging
gh workflow run deploy.yml -f environment=staging

# Deploy to production
gh workflow run deploy.yml -f environment=production
```

### Running Utilities
```bash
# Generate release notes
gh workflow run utilities.yml -f action=release-prep

# Run stale check manually
gh workflow run utilities.yml -f action=stale-check

# Generate metrics report
gh workflow run utilities.yml -f action=metrics-report
```

## Migration from Old Workflows

The following workflows have been replaced:
- `backend-ci.yml` → Integrated into `ci.yml`
- `frontend-ci-simple.yml` → Integrated into `ci.yml`
- `coverage.yml` → Integrated into `ci.yml`
- `security.yml` → Integrated into `ci.yml`
- `quality-gates.yml` → Integrated into `ci.yml`
- `pr-automation.yml` → Replaced by `utilities.yml`

## Best Practices

1. **Always pin actions to commit SHAs** for security
2. **Use composite actions** for repeated logic
3. **Implement proper caching** to speed up builds
4. **Run tests in parallel** when possible
5. **Use matrix strategies** for comprehensive testing
6. **Implement retry logic** for flaky operations
7. **Keep workflows simple** and modular
8. **Document all secrets** required
9. **Monitor workflow performance** and optimize
10. **Regular security audits** of workflows

## Troubleshooting

### Common Issues

1. **Workflow not triggering**
   - Check path filters in workflow
   - Verify branch protection rules
   - Check workflow permissions

2. **Tests failing randomly**
   - Retry mechanism will handle flaky tests (3 attempts)
   - Check service health checks
   - Review timeout configurations

3. **Coverage threshold failures**
   - Current thresholds: Backend 85%, Frontend 85%
   - Run coverage locally to identify gaps
   - Update tests before pushing

4. **Security scan failures**
   - Review security report artifacts
   - Update dependencies if vulnerabilities found
   - Check for hardcoded secrets

### Debug Mode

Enable debug logging:
```bash
gh workflow run ci.yml -f debug=true
```

### Support

For issues or questions:
1. Check workflow logs in GitHub Actions
2. Review this documentation
3. Check `.github/CODEOWNERS` for maintainers
4. Open an issue with the `ci/cd` label

## Maintenance

### Weekly Tasks
- Review Dependabot PRs (grouped by category)
- Check workflow performance metrics
- Update pinned action versions if needed

### Monthly Tasks
- Review and update coverage thresholds
- Audit workflow permissions
- Update composite actions
- Review stale issues/PRs

### Quarterly Tasks
- Major dependency updates
- Security audit of workflows
- Performance optimization review
- Documentation updates