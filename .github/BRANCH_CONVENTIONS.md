# Branch Naming Conventions

This document outlines the standardized branch naming conventions for the TripSage repository and how they integrate with our CI/CD workflows.

## Workflow Trigger Patterns

Our GitHub Actions workflows are configured to trigger on specific branch patterns. All workflows use these standardized patterns:

```yaml
on:
  push:
    branches: [main, develop, feat/*, "session/*"]
  pull_request:
    branches: [main, develop]
```

## Branch Types and Patterns

### 1. Main Branches

#### `main`

- **Purpose:** Production-ready code
- **Triggers:** All workflows (CI, security, coverage, deployment)
- **Protection:** Fully protected, requires PR and reviews
- **Deployment:** Auto-deploys to production (Vercel)

#### `develop`

- **Purpose:** Integration branch for features
- **Triggers:** All workflows except production deployment
- **Protection:** Protected, requires PR and CI passes
- **Deployment:** May auto-deploy to staging

### 2. Feature Branches

#### Pattern: `feat/*`

**Examples:**

```text
feat/user-authentication
feat/trip-collaboration-system
feat/api-rate-limiting
feat/websocket-real-time
feat/accommodation-search
```

**Guidelines:**

- Use kebab-case (lowercase with hyphens)
- Be descriptive but concise
- Start with `feat/` prefix
- Branch from `develop`
- Merge back to `develop` via PR

**Workflow Triggers:**

- ✅ Backend CI (on push)
- ✅ Frontend CI (on push)
- ✅ Security Scanning (on push)
- ✅ Code Coverage Analysis (on push)
- ✅ Quality Gates (on PR to main/develop)

### 3. Session Branches (AI Development)

#### Pattern: `session/*`

**Examples:**

```text
session/create-trip-endpoint
session/fix-authentication-bug
session/performance-optimization
session/claude-ai-refactor-components
```

**Guidelines:**

- Used for AI-assisted development sessions
- Include session purpose or ticket reference
- Temporary branches, delete after merge
- Can branch from any base (main, develop, feat/*)

**Workflow Triggers:**

- ✅ Backend CI (on push)
- ✅ Frontend CI (on push)  
- ✅ Security Scanning (on push)
- ✅ Code Coverage Analysis (on push)
- ✅ Quality Gates (on PR to main/develop)

### 4. Hotfix Branches

#### Pattern: `hotfix/*`

**Examples:**

```text
hotfix/security-patch-v1.2.1
hotfix/critical-memory-leak
hotfix/urgent-auth-fix
```

**Guidelines:**

- For critical production fixes
- Branch directly from `main`
- Merge to both `main` and `develop`
- Version number recommended in name

**Workflow Triggers:**

- ⚠️ Currently not in standard triggers
- Should manually trigger workflows or use workflow_dispatch

### 5. Release Branches

#### Pattern: `release/*`

**Examples:**

```text
release/v1.2.0
release/v2.0.0-beta
release/sprint-23
```

**Guidelines:**

- For release preparation
- Branch from `develop`
- Only bug fixes and release tasks
- Merge to `main` when ready

**Workflow Triggers:**

- ⚠️ Currently not in standard triggers
- Consider adding to workflow patterns for releases

### 6. Documentation Branches

#### Pattern: `docs/*`

**Examples:**

```text
docs/api-documentation
docs/deployment-guide
docs/user-manual-update
```

**Guidelines:**

- For documentation-only changes
- Can branch from any base
- Lightweight review process

**Workflow Triggers:**

- ⚠️ Currently not in standard triggers
- May skip some CI checks for docs-only changes

## Workflow Integration

### Automatic Triggers

| Branch Pattern | Backend CI | Frontend CI | Security | Coverage | Quality Gates | Deploy |
|----------------|------------|-------------|----------|----------|---------------|---------|
| `main` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `develop` | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ |
| `feat/*` | ✅ | ✅ | ✅ | ✅ | ✅ (PR) | ❌ |
| `session/*` | ✅ | ✅ | ✅ | ✅ | ✅ (PR) | ❌ |
| `hotfix/*` | ❌* | ❌* | ❌* | ❌* | ❌* | ❌ |
| `release/*` | ❌* | ❌* | ❌* | ❌* | ❌* | ❌ |

*_Not currently in trigger patterns - requires manual workflow dispatch_

### Quality Requirements by Branch

#### For `main` branch

- ✅ All CI checks must pass
- ✅ Security scans must pass (critical vulnerabilities block merge)
- ✅ Coverage thresholds must be met
- ✅ At least 1 code review approval required
- ✅ Branch must be up to date with main

#### For `develop` branch

- ✅ All CI checks must pass
- ⚠️ Security issues are warnings (not blocking)
- ⚠️ Coverage below threshold is warning
- ✅ Code review recommended but may not be required

#### For feature/session branches

- ✅ CI checks should pass for PR merge
- ℹ️ Work-in-progress commits may have failing checks
- ℹ️ Draft PRs exempt from strict requirements

## Best Practices

### Branch Creation

```bash
# Feature branch
git checkout develop
git pull origin develop
git checkout -b feat/user-profile-management

# Session branch (AI development)
git checkout main  # or any base branch
git pull origin main
git checkout -b session/implement-search-filters

# Hotfix branch
git checkout main
git pull origin main
git checkout -b hotfix/fix-login-redirect
```

### Branch Maintenance

```bash
# Keep feature branch up to date
git checkout feat/my-feature
git merge origin/develop  # or rebase if preferred

# Clean up after merge
git branch -d feat/my-feature
git push origin --delete feat/my-feature
```

### Naming Guidelines

**DO:**

- Use descriptive, meaningful names
- Follow the established patterns
- Use kebab-case (lowercase with hyphens)
- Keep names reasonably short but clear
- Include ticket/issue numbers when relevant

**DON'T:**

- Use spaces or special characters
- Create overly long branch names
- Use generic names like `fix`, `update`, `new-feature`
- Include your name (Git history tracks authors)
- Use camelCase or snake_case

### Examples of Good Branch Names

```text
✅ feat/user-authentication-system
✅ feat/trip-collaboration-v2
✅ session/fix-websocket-connection
✅ session/claude-refactor-api-endpoints
✅ hotfix/security-vulnerability-cve-2024-1234
✅ release/v2.1.0
✅ docs/api-reference-update
```

### Examples of Poor Branch Names

```text
❌ fix-stuff
❌ johns-work
❌ new_feature
❌ updateUserProfileManagementAndAddNewFieldsForBetterUserExperience
❌ temp
❌ test-branch-do-not-merge
```

## Troubleshooting

### Branch Not Triggering Workflows

1. **Check branch name pattern** - Ensure it matches one of the supported patterns
2. **Verify file changes** - Some workflows only trigger on specific file path changes
3. **Check workflow status** - Look in GitHub Actions tab for any errors

### Adding New Branch Patterns

To add support for new branch patterns (e.g., `hotfix/*`, `release/*`):

1. Update all workflow files in `.github/workflows/`
2. Modify the `branches` array in the `on.push` and `on.pull_request` sections
3. Test with a sample branch
4. Update this documentation

### Manual Workflow Triggers

For branches not in the automatic trigger patterns:

```bash
# Using GitHub CLI
gh workflow run "Backend CI" --ref hotfix/my-fix

# Or use the GitHub web interface:
# Actions tab > Select workflow > Run workflow > Choose branch
```

## Migration Guide

If you have existing branches that don't follow these conventions:

1. **Rename local branch:**

   ```bash
   git branch -m old-name feat/new-name
   ```

2. **Update remote branch:**

   ```bash
   git push origin :old-name feat/new-name
   git push --set-upstream origin feat/new-name
   ```

3. **Update any open PRs** to point to the new branch name

## Future Considerations

### Potential Additions

- `hotfix/*` and `release/*` patterns to workflow triggers
- Separate workflow for documentation-only changes
- Integration with linear issue tracking
- Automated branch cleanup for merged branches
- Branch naming validation in PR automation

### Workflow Optimizations

- Skip certain checks for docs-only changes
- Faster CI for hotfix branches
- Parallel execution optimizations
- Smarter caching strategies based on branch type
