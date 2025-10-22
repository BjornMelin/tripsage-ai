# Repository Setup Guide

This document provides instructions for setting up a new TripSage
repository with all required secrets, configurations, and CI/CD workflows.

## Required Repository Secrets

The following secrets must be configured in your GitHub repository settings
(`Settings > Secrets and variables > Actions`):

### Code Coverage & Quality

| Secret Name | Purpose | Required For | How to Obtain |
|-------------|---------|--------------|---------------|
| `CODECOV_TOKEN` | Upload coverage | Backend, Frontend | See setup below |

### Deployment Secrets (Vercel)

| Secret Name | Purpose | Required For | How to Obtain |
|-------------|---------|--------------|---------------|
| `VERCEL_TOKEN` | Deploy to Vercel | Deploy workflow | See Vercel setup below |
| `VERCEL_ORG_ID` | Vercel org ID | Deploy workflow | See Vercel setup below |
| `VERCEL_PROJECT_ID` | Vercel project ID | Deploy | See Vercel setup below |

### Optional Secrets

| Secret Name | Purpose | Required For | Notes |
|-------------|---------|--------------|-------|
| `GITHUB_TOKEN` | GitHub API access | Automatic | No setup required |

### Detailed Setup Instructions

**Codecov Setup:**

1. Sign up at [codecov.io](https://codecov.io)
2. Connect your GitHub repository
3. Copy the repository token from Codecov dashboard

**Vercel Token Setup:**

1. Go to [Vercel Account Settings](https://vercel.com/account/tokens)
2. Create a new token
3. Copy the generated token

**Vercel Project Setup:**

1. Run `npx vercel link` in your project
2. Check `.vercel/project.json` for `orgId` and `projectId`
3. Or find in Vercel dashboard under project/team settings

## Repository Configuration

### 1. Branch Protection Rules

Configure branch protection for `main` and `develop` branches:

```bash
# Navigate to: Settings > Branches > Add rule

Branch name pattern: main
☑️ Require a pull request before merging
☑️ Require approvals (minimum: 1)
☑️ Dismiss stale PR approvals when new commits are pushed
☑️ Require review from code owners
☑️ Require status checks to pass before merging
    Required status checks:
    - Quality Gates Summary
    - Backend CI / quality-gate
    - Frontend CI / quality-gate
    - Security Scanning / security-summary
☑️ Require branches to be up to date before merging
☑️ Require linear history
☑️ Require deployments to succeed before merging
☑️ Do not allow bypassing the above settings
```

### 2. Repository Settings

**General Settings:**

- ☑️ Allow merge commits
- ☑️ Allow squash merging (recommended for feature branches)
- ☑️ Allow rebase merging (recommended for hotfixes)
- ☑️ Always suggest updating pull request branches
- ☑️ Automatically delete head branches

**Security & Analysis:**

- ☑️ Enable Dependency graph
- ☑️ Enable Dependabot alerts
- ☑️ Enable Dependabot security updates
- ☑️ Enable Secret scanning
- ☑️ Enable Push protection for secret scanning
- ☑️ Enable Code scanning

## Branch Naming Conventions

Our CI/CD workflows are configured to trigger on specific branch patterns:

### Supported Branch Patterns

| Pattern | Purpose | Example | Triggers |
|---------|---------|---------|----------|
| `main` | Production branch | `main` | All workflows |
| `develop` | Development integration | `develop` | All workflows except deploy |
| `feat/*` | Feature branches | `feat/user-auth` | CI, security, coverage |
| `session/*` | Session development | `session/claude-ai-123` | CI, security |

### Branch Naming Guidelines

**Feature Branches:**

```bash
feat/user-authentication
feat/trip-collaboration
feat/api-rate-limiting
```

**Session Branches (for AI-assisted development):**

```bash
session/create-trip-endpoint
session/fix-auth-bug
session/performance-optimization
```

**Hotfix Branches:**

```bash
hotfix/security-patch-v1.2.1
hotfix/critical-memory-leak
```

**Release Branches:**

```bash
release/v1.2.0
release/v2.0.0-beta
```

## Workflow Dependencies

### Required Workflows

Our quality gates depend on these core workflows:

1. **Backend CI** (`backend-ci.yml`)
   - Code quality checks (ruff, mypy)
   - Unit tests with coverage
   - Integration tests
   - Security scans (bandit)

2. **Frontend CI** (`frontend-ci-simple.yml`)
   - TypeScript compilation
   - Lint checks (Biome)
   - Unit tests with coverage
   - Build validation
   - E2E tests (optional)

3. **Security Scanning** (`security.yml`)
   - Secret detection (TruffleHog)
   - Python security analysis (bandit, safety, semgrep)
   - Frontend security checks
   - Dependency vulnerability scanning
   - Docker security analysis

4. **Code Coverage Analysis** (`coverage.yml`)
   - Combined backend and frontend coverage
   - Coverage threshold enforcement
   - Trend analysis

### Quality Gates

The `quality-gates.yml` workflow aggregates results from all CI workflows:

- ✅ **Backend CI** must pass
- ✅ **Frontend CI** must pass  
- ✅ **Security Scanning** must pass (critical for main branch)
- ✅ **Code Coverage** must meet thresholds

## Setup Checklist

### Initial Repository Setup

- [ ] Clone repository
- [ ] Configure all required secrets in GitHub repository settings
- [ ] Set up branch protection rules for `main` and `develop`
- [ ] Configure repository settings (merge options, security features)
- [ ] Test workflows by creating a test PR

### Development Environment Setup

**Backend:**

```bash
# Install dependencies
uv sync --group dev

# Run tests to verify setup
uv run pytest tests/unit/ -v

# Run linting
ruff check . --fix
ruff format .
```

**Frontend:**

```bash
cd frontend

# Install dependencies  
pnpm install

# Run tests
pnpm test

# Run linting
npx biome lint --apply .
npx biome format . --write
```

### Vercel Deployment Setup

1. **Link Project to Vercel:**

   ```bash
   cd frontend
   npx vercel link
   ```

2. **Extract Project Configuration:**

   ```bash
   # Check .vercel/project.json for:
   cat .vercel/project.json
   # Copy "orgId" to VERCEL_ORG_ID secret
   # Copy "projectId" to VERCEL_PROJECT_ID secret
   ```

3. **Configure Environment Variables in Vercel:**
   - Go to Vercel dashboard > Project Settings > Environment Variables
   - Add production environment variables as needed

### Codecov Setup

1. **Sign up at codecov.io** and connect your GitHub repository
2. **Copy repository token** from Codecov dashboard
3. **Add token** to GitHub repository secrets as `CODECOV_TOKEN`
4. **Verify coverage uploads** after running CI workflows

## Troubleshooting

### Common Issues

**"ruff: command not found" in Backend CI:**

- ✅ Fixed: Added explicit ruff installation step

**Inconsistent branch triggers:**

- ✅ Fixed: Standardized all workflows to use `[main, develop, feat/*, "session/*"]`

**Missing Codecov token:**

- Add `CODECOV_TOKEN` secret to repository settings
- Token can be found in Codecov dashboard after connecting repository

**Vercel deployment fails:**

- Verify all three Vercel secrets are correctly configured
- Check that `vercel.json` configuration is valid
- Ensure build command succeeds locally

**Quality gates always fail:**

- Check that all required workflows are completing successfully
- Verify coverage thresholds are achievable
- Review security scan results for critical issues

### Workflow Debugging

**Check workflow runs:**

```bash
# Using GitHub CLI
gh run list --workflow="Backend CI"
gh run view <run-id> --log
```

**Local testing:**

```bash
# Test backend locally
uv run pytest tests/unit/ --cov=tripsage --cov=tripsage_core

# Test frontend locally  
cd frontend && pnpm test:coverage
```

## Support

For additional help:

- Review workflow logs in GitHub Actions tab
- Check individual job outputs for specific error messages
- Verify all secrets are correctly configured
- Ensure branch naming follows established conventions

## Security Notes

- Never commit real secrets to the repository
- Use GitHub secrets for all sensitive configuration
- Regularly rotate API tokens and keys
- Review security scan results and address critical vulnerabilities
- Keep dependencies updated to avoid known vulnerabilities
