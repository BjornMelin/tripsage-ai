# ADR-0055: Flatten Next.js App Structure to Repository Root

**Version:** 1.0.0
**Status:** Accepted
**Date:** 2025-12-08  
**Category:** Architecture  
**Domain:** Frontend  
**Related ADRs:** ADR-0013 (Next.js 16 Proxy Adoption)【46†L31-L39】, ADR-0016 (Tailwind CSS v4 Config)【46†L33-L36】  
**Related Specs:** SPEC-0002 (Next.js 16 Migration)【39†L29-L37】

## Current Implementation Status

This ADR is implemented. The live repository has no top-level `frontend/`
directory; the Next.js app runs from the repository root with `src/`,
`package.json`, `pnpm-lock.yaml`, `next.config.ts`, `tsconfig.json`, and
`pnpm-workspace.yaml` at root. Use `AGENTS.md` and
[`docs/architecture/repo-structure.md`](../repo-structure.md) for current
repo-structure rules. The context and alternatives below describe the
pre-flattening state and the decision that removed it.

## Context

Before this ADR was implemented, the TripSage repository isolated the Next.js application in a top-level `frontend/` directory. All source code, dependencies, and configuration for the app lived under `frontend/`, with infrastructure (Supabase, Docker, docs, etc.) at the root. This split originated to separate concerns (and perhaps to allow multi-package expansion), but in practice TripSage is a single application. The indirection added complexity:

- Developer workflow friction: Contributors must remember to change directory into `frontend/` for nearly every action, for example installing packages, running `pnpm dev`, tests, linting, etc.【2†L75-L83】. Missing this step leads to confusion (for example running commands in root does nothing or operates on a different context).
- Duplicate configuration: Many config files exist in or refer to `frontend/` where a single config at root would suffice. Examples: separate `frontend/package.json`, `frontend/.npmrc`【63†L1-L4】, `frontend/tsconfig.json` (with path aliases), and a root `.nvmrc` and `Makefile` that assume the subdir. This duplication requires coordination, for example Node version is defined in root, but `pnpm-lock.yaml` is inside frontend.
- CI/CD complexity: The GitHub Actions workflows target `frontend` paths explicitly【48†L49-L58】【48†L69-L77】. The deployment (for example Vercel) is likely configured with `frontend` as the project root. These hardcoded references mean any structural change (or a simple oversight in path) can break the pipeline.
- Next.js best practices: Next.js (especially App Router projects) usually reside at the repo root or under a `src/` folder, not an extra monorepo-style folder, unless there are multiple apps. Here we have one app, so the indirection is unnecessary.
- Maintenance overhead: Every update needs to touch both root and `frontend` in some way. For example, Dependabot or version bumps might update root config and frontend separately. Code owners file lists many `frontend/*` patterns【70†L25-L34】 that need mirroring if structure changes. This creates opportunities for inconsistency and increases cognitive load (developers must remember “frontend” prefix everywhere).

In short, the old structure was a remnant of a potential monorepo architecture that was not needed. Simplifying to a single unified project directory reduced errors and onboarding time, and made the repository align with community norms.

## Decision

We flattened the Next.js application structure by moving all contents of `frontend/` to the repository root, establishing a single-package architecture. Concretely:

- The `frontend/src` directory became `src` at root. The Next.js app’s entry (`src/app` with all route files) stayed the same relative to `src`, just with no parent `frontend` folder.
- Config and support files in `frontend/` were moved or merged into root. For example, `frontend/package.json` became the root `package.json`, and `frontend/tsconfig.json` moved to root with paths adjusted as required.
- Redundant or conflicting files were resolved. Root documentation became the main documentation surface, while superseded frontend-specific guidance was folded into root docs or archived.
- Build and runtime configs were updated to reflect the new layout:
  - Next.js config (`next.config.ts`) resides at root. Settings such as `turbopack.root` were reviewed so `"."` points to the repository root.
  - Tailwind/PostCSS config follows the Tailwind CSS v4 CSS-first approach from root.
  - Path aliases formerly defined in `frontend/tsconfig.json` (like `"@/*": ["src/*"]`, `"@domain/*": ["src/domain/*"]`) remain logically the same from the root `tsconfig.json`.
- Tooling adjustments:
  - CI workflows: GitHub Actions YAML was updated to use the repository root as the working directory and root path filters such as `src/**` instead of `frontend/**`.
  - Ownership and governance files were updated where applicable to remove `/frontend/` ownership patterns and use root or `src/` patterns instead.
  - Dev scripts: `package.json` scripts and npm config assumptions were moved to root. Scripts referencing paths like `frontend/coverage` were updated to root paths.
- Documentation: README and active docs references to `cd frontend` or old `frontend/` app paths were updated to the new locations. The primary README quick start simplified to root commands such as `pnpm install && pnpm dev` (no subdirectory step). Architecture docs removed the extra layer in diagrams or text.

This decision aligned the repository with the one-app reality and modern Next.js project conventions. It eliminated the cost of maintaining parallel structures and reduced potential for mistakes.

## Consequences

### Positive

- Developer efficiency: New contributors can get the app running with fewer steps. The risk of running tests or builds in the wrong directory disappears. IDEs and tools will auto-detect config (TS, ESLint, etc.) more easily at root.
- Simpler CI/CD: One build context means simpler workflows. No need for `working-directory: frontend` hacks. Caching and path globs become straightforward. This reduces maintenance of CI (for example, after this change we will not have to double-list paths or worry about missing a `frontend/` prefix in some script).
- Reduced duplication: With one `package.json` and unified config files, there is a single source of truth for dependencies and settings. For instance, version bumps will happen in one place. Tools like Dependabot or Renovate will operate on one package file.
- Convention alignment: Following standard project structure makes it easier for community members or future hires to navigate the repo. Many assumptions (like “app lives at root/src/app” or “tailwind.config.js is at project root”) will just work, with less special-case knowledge needed.
- Path simplicity: Error messages, stack traces, coverage reports, etc. will be easier to read without the extra directory level. Searching the repo is also a bit easier (one less level to specify).

### Negative / Risks

- Merge conflict risk: This is a large file move. Pending PRs or branches will experience conflicts. We should coordinate this change in a quiet period or communicate clearly so that others pause development or merge in changes beforehand. The ADR being accepted signals everyone to prepare for a one-time disruption.
- Deployment reconfiguration: The Vercel project or whichever deployment target must be updated to use the repository root as the app location. Missing this could break the production deploy until corrected. It is a one-time setup tweak.
- Blame history loss: Moving files will complicate `git blame` history, unless we use tools to trace through renames. We mitigate this by using `git mv` so history is preserved, but in some cases, such as editing lines during the move, attribution could be lost. This is a minor trade-off given the long-term benefits.
- Potential oversights: It is possible to miss an indirect reference to `frontend` in some script, README, or GitHub setting. For example, the release script was referencing `../CHANGELOG.md` from `frontend` context【65†L21-L29】. Such things must be adjusted. A thorough search for `frontend/` will be needed. Even after that, the first pipeline run or local start after refactor will be a crucial test to catch anything missed.
- No immediate user benefit: This refactor does not add features or fix a user-facing bug. It is purely internal improvement. If not managed well, it could introduce a bug. We accept this risk because the long-term velocity and stability improvements justify a short-term pause in feature delivery.

### Neutral

- Repository size and structure: The overall repo contents remain the same, just organized differently. Docker, Supabase, docs, etc. continue to live at root as they do. We are not deleting code, except perhaps obsolete config files, mostly moving. Build output (`.next/`) will now be at root instead of `frontend/.next`, but that is inconsequential outside of CI caching adjustments.
- Tooling config changes: Some config values (paths in tsconfig, etc.) will change, but the behavior should remain the same. For example, path aliases still point to the same code. The team will need to adapt to running commands from root, but that is a return to normal, not a new requirement. This might actually be positive, but we list it as neutral since it is a change in habit.

## Alternatives Considered

### Alternative 1: Keep `frontend/` structure, refine it

We could retain the `frontend` folder and just improve tooling around it, for example adjust root scripts to proxy commands into `frontend/`, so developers could run `pnpm dev` at root and it would internally do `(cd frontend && pnpm dev)`. This would hide some complexity but not remove it. CI could similarly be tricked to run from root and target frontend.

Why not chosen: This approach is essentially layering more complexity to mask an existing complexity. It does not eliminate the duplication of config or the potential for mismatches, it merely automates some of the steps. It also goes against the grain of typical Next.js projects, meaning new contributors still need to learn our special setup. The maintenance burden of scripts to forward commands is non-trivial and could break in edge cases. Overall, it is a band-aid that fails to address the root issue: the unnecessary extra layer.

### Alternative 2: Multi-Package Monorepo Expansion

Another path considered was to actually justify the `frontend/` directory by expanding the repo into a true monorepo, for example adding a `backend/` service or splitting out libraries. If TripSage were to have multiple deployables, the `frontend` folder could become one of many packages managed via a workspace (pnpm workspaces or Nx, etc.). In that scenario, we would invest in the monorepo tooling and perhaps keep the structure.

Why not chosen: This is currently YAGNI, “You Are Not Gonna Need It”. There is no second app or service in scope. The Next.js app already serves as backend with API routes and frontend. Splitting out further microservices would add complexity and overhead not justified by our scale, and could be hosted separately if needed. Maintaining a monorepo toolchain for a single package makes little sense. If in the future a compelling need for multiple packages arises, we can re-evaluate, but it would likely use a different structure and perhaps a turbo repo or similar. For now, we optimize for the present state, one app.

## References

- Next.js App directory layout recommendations【9†L58-L66】 and community examples that keep the app at repo root.
- ADR-0013: Adopt Next.js 16 Proxy (noted the removal of old `middleware.ts`, which simplified root structure dependencies)【46†L31-L39】.
- ADR-0016: Tailwind v4 migration, which chose a no-config approach we will uphold after flattening【46†L33-L36】.
- Internal discussion in [Import Paths](../../development/standards/standards.md#import-paths) on path aliases, which will remain consistent after flattening but defined in root tsconfig【23†L73-L81】.
- Changelog entry on updating Turbopack root to "."【68†L1-L4】, relevant to ensure Next’s config still points correctly post-move.
