# Contributing to TripSage

We welcome contributions from the community! This guide outlines how to get started with development, submit changes, and maintain code quality.

## Development Workflow

Follow these steps to contribute effectively:

1. **Fork** the repository and clone your fork locally.
2. **Create** a feature branch: `git checkout -b feature/amazing-feature`.
3. **Write** tests for your changes (aim for 90%+ coverage using pytest for backend and Vitest for frontend).
4. **Run tests and linting**:
   - Backend: `uv run pytest` (unit/integration) and `ruff check . --fix && ruff format .`.
   - Frontend: `cd frontend && pnpm test && npx biome lint --apply .`.
5. **Commit** your changes with a conventional message: `git commit -m 'feat: add amazing feature'`.
6. **Push** to your branch: `git push origin feature/amazing-feature`.
7. **Open** a Pull Request (PR) on the main repo, linking any related issues. Ensure the PR description includes what was changed, why, and any testing done.

All changes must pass CI (linting, types, tests, coverage) before merging. Use conventional commits (e.g., `feat:`, `fix:`, `docs:`) for changelog generation.

## Code Standards

Follow our [Code Standards](code-standards.md) for Python (PEP-8, ruff), TypeScript (Biome, strict mode), and general guidelines (type hints, docstrings).

## Testing

Refer to the [Testing Guide](testing-guide.md) for details on unit, integration, and E2E tests. Maintain 90%+ coverage and use fixtures/factories for deterministic tests.

## Additional Guidelines

- **Branch Naming**: Use `feat/`, `fix/`, `docs/` prefixes (e.g., `feat/add-flight-search`).
- **PR Reviews**: Expect feedback on design, tests, and standards. Address all comments before merging.
- **Releases**: Changes are included in semantic versions based on commit types.

For more, see [Code Standards](code-standards.md) and [Testing Guide](testing-guide.md). Questions? Open an issue or discuss in GitHub Discussions!
