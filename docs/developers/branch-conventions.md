# Branch Conventions

Standardized branch naming conventions and workflow integration.

## Branch Types

### Main Branches

| Branch | Purpose | Protection | CI/CD |
|--------|---------|------------|-------|
| `main` | Production code | PR required, reviews needed | Full CI + deployment |
| `develop` | Feature integration | PR required, CI must pass | Full CI, staging deploy |

### Feature Branches

**Pattern:** `feat/*`

**Examples:**

- `feat/user-authentication`
- `feat/trip-planning`
- `feat/api-improvements`

**Workflow:**

1. Create from `develop`
2. Implement feature
3. Create PR to `develop`
4. Delete after merge

### Session Branches

**Pattern:** `session/*`

**Examples:**

- `session/user-auth-flow`
- `session/database-optimization`

**Use:** Temporary branches for focused work sessions

### Hotfix Branches

**Pattern:** `hotfix/*`

**Examples:**

- `hotfix/critical-security-fix`
- `hotfix/database-connection-issue`

**Workflow:**

1. Create from `main`
2. Fix critical issue
3. Create PR to both `main` and `develop`

### Release Branches

**Pattern:** `release/*`

**Examples:**

- `release/v1.2.0`
- `release/v2.0.0`

**Use:** Release preparation and final testing

## CI/CD Integration

### Workflow Triggers

```yaml
on:
  push:
    branches: [main, develop, feat/*, session/*]
  pull_request:
    branches: [main, develop]
```

### Branch-Specific Pipelines

| Branch Pattern | Tests | Linting | Security | Deployment |
|----------------|-------|---------|----------|------------|
| `main` | ✅ | ✅ | ✅ | ✅ Production |
| `develop` | ✅ | ✅ | ✅ | ✅ Staging |
| `feat/*` | ✅ | ✅ | ✅ | ❌ |
| `session/*` | ✅ | ✅ | ✅ | ❌ |
| `hotfix/*` | ❌ | ❌ | ❌ | ❌ |
| `release/*` | ❌ | ❌ | ❌ | ❌ |

## Guidelines

### Branch Naming

- Use lowercase with hyphens: `feat/user-login`
- Be descriptive but concise
- Start with category: `feat/`, `hotfix/`, `session/`
- Avoid special characters except hyphens

### Pull Requests

- Target `develop` for features
- Target `main` for hotfixes and releases
- Include description of changes
- Reference issues/tickets
- Request appropriate reviewers

### Commit Messages

Use conventional commits:

```text
feat: add user authentication
fix: resolve database connection timeout
docs: update API documentation
```

### Branch Lifecycle

- Create branches from appropriate base
- Keep branches focused on single feature/fix
- Rebase frequently to stay current
- Delete merged branches promptly
