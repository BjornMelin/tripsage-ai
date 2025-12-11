# Release Automation (semantic-release)

This repository uses semantic-release to automate versioning, changelog updates, tags, and GitHub Releases on pushes to `main`.

## Workflow

- Trigger: push to `main`.
- Action: `.github/workflows/release.yml`.
- Steps: checkout (full history) → set up Node from `.nvmrc` → install pnpm and dependencies → run `npx semantic-release --extends release.config.mjs`.
- Env: `GITHUB_TOKEN` and `NPM_TOKEN` (required for `@semantic-release/npm` verify step even though we do not publish).
- Permissions: `contents`, `issues`, and `pull-requests` (write) to create tags and release notes.

## Configuration

File: `release.config.mjs` (root).

- semantic-release runs from repo root.
- Plugins:
  - `@semantic-release/commit-analyzer` with temporary rule `{ breaking: true, release: 'minor' }`.
  - `@semantic-release/release-notes-generator` (conventional commits preset).
  - `@semantic-release/changelog` updates `CHANGELOG.md` (repo root).
  - `@semantic-release/npm` bumps `package.json` with `npmPublish: false` (version only, no npm publish).
  - `@semantic-release/git` commits `CHANGELOG.md` + `package.json` with `chore(release): <version> [skip ci]`.
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

3. Push to `main` to run the release workflow.
4. Update release docs to state majors are enabled.

## Commit conventions (recap)

- `feat:` → minor; `fix:` → patch; other prefixes for non-releasing work (`chore:`, `docs:`, `ci:`).
- Breaking changes: add `BREAKING CHANGE:` footer describing the impact.

## Rollback

If a release is incorrect:

1. Delete the Git tag and GitHub Release for that version.
2. Revert the auto-commit that updated `CHANGELOG.md` and the `@semantic-release/npm` version bump in `package.json` (if present).
3. Fix the offending change or config, then rerun the workflow by pushing to `main`.

## Troubleshooting

- **No release produced**: ensure the commit history since the last tag contains a `feat` or `fix` (or `breaking` with the temporary rule). Non-releasing prefixes are ignored.
- **Permissions error**: confirm workflow permissions include `contents: write`.
- **Branch protection blocks release commit**: allow GitHub Actions (`GITHUB_TOKEN`) to push to `main`, or add a bypass rule for the release job so `@semantic-release/git` can commit `chore(release): …` and update `CHANGELOG.md`/`package.json`.
- **Unexpected major**: verify the `releaseRules` still map `breaking` to `minor`.
- **Changelog not updating**: check that `@semantic-release/changelog` and `@semantic-release/git` are installed and present in the config.
