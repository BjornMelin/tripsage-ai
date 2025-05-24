# CI/CD Pipeline Documentation

This directory contains GitHub Actions workflows for the TripSage AI project.

## Workflows

### 1. Frontend CI/CD (`frontend-ci.yml`)
**Comprehensive workflow for frontend testing and deployment**

- **Triggers**: Push/PR to main/develop branches with frontend changes
- **Jobs**:
  - **Lint and Format**: Biome linting/formatting + ESLint
  - **Unit Tests**: Vitest with coverage reporting
  - **Build**: Next.js production build with caching
  - **E2E Tests**: Playwright tests against built application
  - **Type Check**: TypeScript strict type checking
  - **Security Audit**: NPM audit for vulnerabilities
  - **Deployment Check**: Validates all checks before deployment

### 2. Frontend CI Simple (`frontend-ci-simple.yml`)
**Simplified workflow focusing on successful builds**

- **Triggers**: Push/PR to main/develop/feat/* branches
- **Jobs**:
  - **Build and Test**: Essential checks for build success
  - Includes dependency installation, build, formatting, and security audit
  - More lenient than comprehensive CI for rapid iteration

### 3. Deployment (`deploy.yml`)
**Vercel deployment automation**

- **Triggers**: 
  - Push to main branch
  - Successful completion of Frontend CI/CD workflow
- **Jobs**:
  - **Production Deploy**: Deploys to Vercel production
  - **Preview Deploy**: Creates preview deployments for PRs

### 4. Dependabot (`dependabot.yml`)
**Automated dependency updates**

- **Schedule**: Weekly on Mondays at 9:00 AM
- **Scope**: 
  - Frontend NPM packages (grouped by type)
  - Python dependencies
  - GitHub Actions
- **Configuration**: Auto-assigns to @BjornMelin for review

## Setup Requirements

### Environment Variables
Add these secrets to your GitHub repository:

```bash
# Vercel deployment
VERCEL_TOKEN=your_vercel_token
VERCEL_ORG_ID=your_org_id
VERCEL_PROJECT_ID=your_project_id

# Optional: Code coverage
CODECOV_TOKEN=your_codecov_token
```

### Branch Protection
Recommended branch protection rules for `main`:

- Require status checks to pass before merging
- Require branches to be up to date before merging
- Required status checks:
  - `Frontend CI/CD / Build Application`
  - `Frontend CI/CD / Lint and Format`
  - `Frontend CI/CD / Unit Tests`

## Workflow Features

### Build Caching
- Next.js build cache using GitHub Actions cache
- Dependency caching with pnpm
- Significantly reduces build times

### Test Coverage
- Vitest unit tests with coverage reporting
- Playwright E2E tests with HTML reports
- Coverage uploads to Codecov (if configured)

### Quality Checks
- Biome for fast linting and formatting
- ESLint for additional React/Next.js rules
- TypeScript strict type checking
- Security vulnerability scanning

### Deployment
- Automatic production deployment on main branch
- Preview deployments for pull requests
- Vercel integration with optimized builds

## Usage

### For Development
1. Create feature branch: `git checkout -b feat/your-feature`
2. Make changes in `frontend/` directory
3. Push to trigger CI: `git push origin feat/your-feature`
4. Create PR to see preview deployment

### For Production
1. Merge PR to main branch
2. Automatic deployment to production
3. Monitor deployment status in GitHub Actions

## Troubleshooting

### Common Issues

**Build Failures**:
- Check Node.js version compatibility (uses Node 20)
- Verify pnpm lockfile is up to date
- Review build logs for specific errors

**Test Failures**:
- Unit tests may fail due to incomplete mocking
- E2E tests require successful build
- Check test reports in GitHub Actions artifacts

**Deployment Issues**:
- Verify Vercel secrets are configured
- Check Vercel project settings
- Review deployment logs in Vercel dashboard

### Getting Help
- Check GitHub Actions logs for detailed error messages
- Review individual job outputs
- Use simple CI workflow for rapid iteration during development