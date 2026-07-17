# Release Automation (semantic-release)

This repository uses semantic-release to automate versioning, changelog updates, tags, and GitHub Releases after CI succeeds for a push to `main`.

## Workflow

- Trigger: successful `CI` workflow completion for a push to `main`.
- Action: `.github/workflows/release.yml`.
- Steps: checkout the tested CI head without persisted credentials (full
  history) → validate tag ancestry → set up Node from `.nvmrc` → install pnpm
  and dependencies → run `pnpm exec semantic-release --extends release.config.mjs`.
- Secret: `RELEASE_BOT_TOKEN`. Only the semantic-release step receives this
  token so the generated release commit triggers CI. The workflow fails closed
  when the secret is absent; `github.token` is intentionally not a fallback.
- Permissions: the built-in workflow token has read-only repository contents
  access. `RELEASE_BOT_TOKEN` supplies the narrowly scoped Git and GitHub API
  write access needed by semantic-release.

## Configuration

File: `release.config.mjs` (root).

- semantic-release runs from repo root.
- Git tags and GitHub Releases are the canonical application version. The
  private root package intentionally omits a separate `package.json#version`.
- Plugins:
  - `@semantic-release/commit-analyzer` with temporary rule `{ breaking: true, release: 'minor' }`.
  - `@semantic-release/release-notes-generator` (conventional commits preset).
  - `@semantic-release/changelog` updates `CHANGELOG.md` (repo root).
  - `@semantic-release/git` commits `CHANGELOG.md` with `chore(release): <version>`.
    That commit runs CI so the exact tagged head receives a deployable provenance
    receipt. The release workflow ignores the successful CI completion for
    `chore(release):` commits to prevent a second semantic-release run.
  - `@semantic-release/github` creates the GitHub Release.

## Temporary major suppression

- During pre-stable, breaking changes are **downgraded to minor bumps** via `releaseRules`.
- Breaking commits still need a `BREAKING CHANGE:` footer for clarity, but they won’t publish a major until we switch to stable.

## Enabling true majors (stable)

When ready to ship the first stable major (e.g., `v2.0.0`):

1. Remove the `{ breaking: true, release: 'minor' }` rule (or change it to `release: 'major'`).
2. Optionally force the first stable tag:

   ```bash
   git tag v2.0.0
   git push origin v2.0.0
   ```

3. Push to `main`; the release workflow runs after CI succeeds.
4. Update release docs to state majors are enabled.

## Commit conventions (recap)

- `feat:` → minor; `fix:` → patch; other prefixes for non-releasing work (`chore:`, `docs:`, `ci:`).
- Breaking changes: add `BREAKING CHANGE:` footer describing the impact.

## Rollback

If a release is incorrect:

1. Delete the Git tag and GitHub Release for that version.
2. Revert the auto-commit that updated `CHANGELOG.md` (if present).
3. Fix the offending change or config, then rerun the workflow by pushing to `main`.

## Troubleshooting

- **No release produced**: ensure the commit history since the last tag contains a `feat` or `fix` (or `breaking` with the temporary rule). Non-releasing prefixes are ignored.
- **Permissions error**: confirm `RELEASE_BOT_TOKEN` is present, valid, and has
  the repository contents, issues, and pull-request write access required by
  the configured semantic-release plugins.
- **Branch protection blocks release commit**: grant the identity behind
  `RELEASE_BOT_TOKEN` the narrow ruleset bypass needed for the release job to
  commit `chore(release): …` and update `CHANGELOG.md`.
- **Unexpected major**: verify the `releaseRules` still map `breaking` to `minor`.
- **Changelog not updating**: check that `@semantic-release/changelog` and `@semantic-release/git` are installed and present in the config.
