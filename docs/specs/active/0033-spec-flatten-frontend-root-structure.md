# Flatten Next.js App Structure - Functional & Technical Spec

## 1. Summary

Flatten the project structure by moving the Next.js application out of the `frontend/` subdirectory to the repository root. This change consolidates all application code, configuration, and dependencies into a single unified project. The flattening will improve developer experience, with one directory to manage, reduce configuration redundancy, and align the repo with standard Next.js practices.

In practical terms, after this change developers will:

- Run all commands, including dev server, tests, builds, from the repo root.
- Find all source code under `/src` at the root instead of `frontend/src`.
- Use a single `package.json` and lockfile at root for all Node dependencies.
- Have all config files, including Next.js, Tailwind, and Vitest, at root, simplifying toolchain setups.

No end-user features are added or removed by this refactor. It should be entirely transparent to users when deployed. The app’s behavior and API endpoints remain the same.

## 2. Goals

- Single-app repository: Achieve a structure where TripSage AI is one logical application at the top level, making local development and CI/CD pipelines straightforward.
- Preserve functionality: After flattening, the application should run exactly as before, with all routes functional and all tests passing. The refactor should not introduce regressions.
- Unified configuration: Merge or update configuration such that there is exactly one of each relevant config file, one package.json, one tsconfig, etc., and they reflect the new paths.
- Developer ergonomics: Make it so common tasks, including install, run, test, require no extra navigation. `pnpm install` at root should install all needed packages, and `pnpm dev` at root should start the Next.js app on port 3000.
- Documentation and scripts: Update all documentation, comments, and scripts to remove references to the `frontend/` subfolder. After the change, a developer reading docs or running a script should not encounter stale instructions related to the old structure.

## 3. Non-Goals

- Introducing new features or upgrades: This spec does not include upgrading dependencies, changing Next.js version, altering Tailwind strategy, and similar. We will carry over the existing code and configs with minimal tweaks for path changes. Any library upgrades, such as AI SDK version bumps, are out of scope.
- Reorganizing internal modules: Aside from moving `src` up one level, we are not significantly refactoring the internal code structure. For example, we will not split the code into multiple packages or move files between `src/components` and `src/domain`. The focus is the directory move, not re-architecting module boundaries.
- Performance optimizations: Any build speed or runtime performance changes from flattening, which are likely negligible, are not intended goals. We do not plan to enable new Next.js features like Turborepo or monorepo linking in this task.
- Changing hosting or deployment strategy: The deployment will still produce a Next.js app artifact as before. We assume the hosting, Vercel for example, remains the same. Only configuration of project path in Vercel might change. We are not introducing new environments or splitting the app.
- Monorepo workspace setup: We will not convert this to a pnpm workspace with multiple packages. After flattening, the repository will have a single `package.json` at root, plus perhaps a `supabase/` CLI config but that is not a Node package. We explicitly choose to simplify to one package rather than expanding to many.

## 4. User Stories

Since this is an internal refactor, users are developers and maintainers of the project.

- As a developer, I want to run the development server without having to `cd` into a subdirectory so that getting the app running is quicker and less error-prone.
- New contributors need a single-root layout with code in `src/` so cloning and navigation stay intuitive.
- DevOps engineers want fewer CI/CD moving parts—no subdirectory installs or path filters—so pipelines remain simple and reliable.
- Technical writers need a straightforward setup story so external docs or README instructions can stay short and clear.
- Project maintainers want to avoid subtle bugs from duplicate configs or misaligned directories (e.g., tsconfig path aliases), improving reliability.

## 5. User Flows

Developer workflows before flattening:

- Local setup: Developer clones repo, changes into `tripsage-ai`, then into `frontend`, then runs `pnpm install` with `frontend/package.json`, copies env files, then runs `pnpm dev`. Running tests similarly requires being in `frontend` or using a root Makefile that itself changes into `frontend`.
- CI pipeline: GitHub Actions triggers on changes in `frontend/**`, then in a job does checkout, setup Node, sets `working-directory: frontend`, installs dependencies, and runs lint/type-check/tests in that subdir.
- Adding a dependency: Developer might accidentally run `pnpm add <pkg>` in root, which would modify a non-existent root package or create one. Instead they must remember to run it in `frontend/`.

Developer workflows after flattening:

- Local setup: Developer clones repo, changes into `tripsage-ai`, runs `pnpm install`, copies `.env.local.example` to `.env.local` at root, and runs `pnpm dev`. The app starts on localhost:3000. There is no need to change directory or run multiple install steps.
- Running tests: From root, `pnpm test` executes Vitest using the root `vitest.config.ts`. All tests run across the `src/` tree. Playwright is run via `pnpm test:e2e`. Coverage is output to `coverage/` at root rather than `frontend/coverage`. A developer does not have to mentally map between root and frontend for results.
- CI pipeline: The GitHub Action triggers on changes to relevant paths, likely now just any push to main or any change in `src/` or config files. The jobs: checkout, setup Node with `.nvmrc` at root, `pnpm install` at root, then `pnpm biome:check`, `pnpm type-check`, and `pnpm test:run`. No `working-directory` indirection is needed. Artifacts and caches use paths like `node_modules/.vite` at root. Deployment job uses the default since the Next app is at root.
- Adding a dependency: Developer runs `pnpm add <pkg>` at root. It updates the single `package.json` and lockfile. No confusion about where to add. All tooling, ESLint, TS, immediately picks it up since they reference the root config.
- Maintaining configs: When updating something like Tailwind content paths or tsconfig compiler options, the developer edits the single source of truth in root config. For example, to include a new directory in Tailwind purge, update `tailwind.config.mjs` at root. There is no second file that could override or conflict.

These flows show a reduction in steps and potential errors. After flattening, developers operate from the repository root for all tasks.

## 6. Data Model & Schemas

There are no changes to the application’s data model or database schema. Flattening the structure does not affect how data is stored or structured in Postgres, Supabase, or any in-memory store. All database tables, Supabase migrations, and pgvector indexes remain as they are.

One related consideration is environment variable schemas. The project likely has a runtime check for required env vars, possibly in `frontend/src/domain/schemas/env.ts`. We must ensure that environment variables are loaded correctly after moving the `.env.local` file:

- Previously, Next.js would load `frontend/.env.local`. After flattening, it will load `.env.local` from the root by default, since Next.js searches the project root directory for env files. This is more straightforward. We should double-check any custom env loading logic, for example if there is a script pointing to `frontend/.env.local` explicitly, and update it.
- The Zod schema for env, if any, will remain the same.

All Zod schemas for API inputs remain in `src/domain/schemas`, just now under root `src/` instead of `frontend/src/`. Their content does not change. No validation logic is affected by this move.

In summary, there are no database or schema changes as part of this spec. We are only concerned with configuration and file paths.

## 7. API Design & Integration Points

The external API, HTTP routes under `/api/*`, remains identical. Flattening does not introduce or remove any API endpoints. Clients of the API will see no difference.

There are a few integration points to adjust internally:

- Next.js application entry: The `app/` directory moves logically, but Next’s resolution will find `src/app` in the new location since that is where `next.config.ts` will point by default. We need to ensure `next.config.ts` is correctly placed at root so that Next picks up the app.
- Environment configuration: Integration with Supabase and Upstash via env vars remains the same. We must verify the `.env` example file is moved and named appropriately so that all required variables, such as `NEXT_PUBLIC_SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `UPSTASH_REDIS_REST_URL`, are loaded. Next.js injects `NEXT_PUBLIC_*` at build, and server-side ones are accessed via `process.env`.
- CI scripts and caching: The CI integration with caching, keyed on lockfile and config files, needs path update. For example, the cache key currently uses `hashFiles('frontend/pnpm-lock.yaml', 'frontend/tsconfig.json', ...)`【48†L55-L63】. After flattening, it should hash `pnpm-lock.yaml` and `tsconfig.json` at root. Similarly, artifact upload/download paths, such as `frontend/.vitest` or `frontend/coverage`, should change to `.vitest` and `coverage`.
- Testing integration: The Vitest config file move means integration with any IDE or CI must point to the new location if there were any direct references. We should run `pnpm test` after move to ensure Vitest picks up the config. The Playwright config similarly should be in root and referenced accordingly.
- Supabase CLI integration: The `Makefile` uses `supabase` CLI commands, for example `make supa.db.push`. These run from root and reference the `supabase/` directory, which remains unchanged. Flattening does not affect Supabase config paths.
- Front-end asset references: Next’s handling of the `/public` folder requires moving any `frontend/public/` assets to `public/` at root. The Next.js app references assets relatively or via the `/` path, which will still resolve, just from the new location.
- Logging and telemetry integration: Vercel’s OTEL is configured via env and import in code, `@vercel/otel`. This likely auto-instruments if the package is present at root. With the code move, the import paths remain the same. We should verify if OTEL was being initialized via a `frontend/otel.ts` file or similar. Any such import may need an updated location.

We should also update or keep `.npmrc` settings which help runtime features, such as hoisting `sharp` for Next Image. These settings can remain in root.

## 8. UI / UX States

There is no change to any UI or UX from an end-user perspective:

- All pages, components, and styles remain as they are. The paths to component files change, but that does not affect the rendered output.
- The UX of uploading a file, planning a trip, chatting with the AI, and similar is untouched by this refactor. If any UI regressions occur, that indicates something went wrong, such as if a component failed to load due to an import path issue.
- The loading and error states in the UI remain the same. We are not modifying any logic around those; we just ensure that error and loading components are correctly located under the `src/app` hierarchy after the move.

To be safe, after refactoring we will do a manual run-through of critical paths:

- Open the app, log in as appropriate, ensure the proxy still sets cookies correctly.
- Trigger an AI chat session, confirm streaming responses still come.
- Navigate through a couple of main pages, trips dashboard, search, etc., to ensure no dynamic import or asset path is broken.

Everything should behave exactly as before.

## 9. Observability & Telemetry

Observability should remain fully intact:

- We will verify that the OpenTelemetry instrumentation still initializes. If OTEL was imported in `frontend/app/_app.tsx` or similar, we ensure the import path is updated if needed, although it should be in a server module under `src/lib/telemetry`.
- Log and trace outputs should continue to go to the same sinks. Because we are not changing any environment variable names or values, the trace collector URL remains configured as before.
- We need to update any log or error messages that include hardcoded path references. For example, a startup log that says “Loaded environment from `frontend/.env.local`” should now refer to `.env.local` at root if such a log exists.
- The Next.js build might output routes; those will naturally not include the `frontend` prefix anymore.

After deployment, we should monitor that traces are coming through as before. If there is an issue, it likely stems from something like `turbopack.root` or source map locations. Since we plan to set `turbopack.root = "."` relative to the new config, we expect no issues.

No changes to metric collection or alerting thresholds are needed; flattening does not change performance profiles significantly.

## 10. Testing Strategy

Testing focus is regression-oriented. We want to ensure everything passes as it did before and that no new issues were introduced by moving files.

- Unit and integration tests: We will run the full Vitest test suite after the move. We expect some path snapshots might need updating if tests assert on file paths or error messages containing paths. For example, a test might assert that a function throws “File not found in /frontend/src/...”. Such an assertion would need to change to the new path or be made path-agnostic.
- E2E tests: Run Playwright tests to ensure the application still functions end-to-end. These tests simulate user behavior, so if something like an API route was incorrectly moved or env not loaded, E2E will catch it. The Playwright config might have a baseURL set, such as `http://localhost:3000` for dev, which remains the same.
- Manual smoke testing: Before merging, a project maintainer will run the app locally and quickly exercise key features, including login, start a chat, create a trip, etc. Because this is structural, we expect if something is broken it will be obvious.
- CI validation: We will rely on the CI pipeline, updated for new paths, to run all checks in a clean environment. The pipeline passing will be the indicator that we did not miss any config.
- Coverage comparison: We will compare test coverage reports before and after flattening. They should be the same. A significant drop or rise could indicate that some tests were not picked up due to path changes. For example, if a glob in Vitest config was wrong after the move, tests might be skipped. We specifically ensure Vitest’s `projects` globs remain correct【21†L121-L130】.
- Tool-specific verifications:
  - Run `pnpm biome:check` after move. It should report no issues, except possibly some unused config references if any.
  - Run `pnpm type-check`. The TS compiler will reveal any import path mistakes.
  - Run `pnpm build` to ensure production build succeeds in root context.
- Boundary check script: Execute `node scripts/check-boundaries.js` to ensure client vs server import rules still pass in the new setup, as they did before【51†L18-L26】【51†L48-L56】.

If tests reveal a severe problem that is not quickly fixable, the change can be reverted, since it is mostly a rename operation. Given thorough checking, we expect to fix forward any minor issues.

## 11. Risks & Open Questions

- Risk: Overlooking a reference. We must search for all references to `frontend/` in the repo, code, docs, GitHub workflows, even README badges or CI config files. Missing one could cause runtime errors or broken documentation. Plan: run `rg "frontend/" -g"*" .`, `rg "\bfrontend\b" .github ci infra scripts`, and scan Vercel/infra repos; capture hits in a checklist PR and require two approvals before merge.
- Risk: Vercel config. Production settings may assume `/frontend`. Update Project Settings → General → Root Directory to `.`, Build & Development → Build Command to `pnpm build`, keep default output. Apply on a preview branch first, validate, then cut production during a low-traffic window with rollback ready.
- Risk: Local environment cache. Developers might have `node_modules` in `frontend/` and none at root. After flattening, one should delete the old `frontend/node_modules` to avoid confusion. We will note this in the migration guide.
- Open question: Keep `src/` or not. Currently, code is in `frontend/src`. After moving to root, we plan to keep `src/`, so code is in `tripsage-ai/src/...`. Alternatively, we could eliminate the `src` folder and put `app/`, `components/`, etc. at root. However, Next.js supports having a `src/` for organizing code, and the team is already using that pattern. Decision: We will preserve the `src` directory to minimize path changes and keep things tidy.
- Open question: What to do with `frontend/README.md`. It contains useful developer-centric info, including tech stack and metrics【4†L0-L8】【4†L119-L127】. We have a few options: merge its content into the main README.md, under a new section or linking to docs, or move it to `docs/development/` if that info is elsewhere. Likely, we will integrate key points into docs and ensure anything redundant with the root README is resolved.
- Risk: Git history and open PRs. Communicate this structural change to the team. There may be open PRs touching files under `frontend/`. We should coordinate to merge those first or prepare them to be rebased after.
- Risk: Path alias edge case. After moving, the tsconfig path aliases like `"@/something"` now map to `src/*` at root. We must verify by running `pnpm biome:check`, `pnpm type-check` (tsc --noEmit), and searching for imports that climb above `src` or point to `frontend/` (including dynamic import/require). Fix any stragglers before merge.
- Open question: Supabase config TOML. It contains runtime sections with paths. If any path like a seed script path was set, we should confirm it is fine. The known changes in config, like `edge_runtime.policy = "oneshot"`【68†L1-L4】, are unrelated to path.
- Risk: Documentation drift. We need to update internal docs to reflect new structure. For example, `docs/development/quick-start.md` likely says `cd frontend`【50†L13-L18】. We must update that. Also, any code snippets in docs pointing to `frontend/src/...` need updating.
- Gain: Reduced future risk. Flattening now reduces the chance of future misconfiguration, such as forgetting to update a setting in two separate places. Addressing this now preempts that class of issues.

Overall, the flattening is straightforward but requires meticulous attention to detail to avoid any service interruption. The plan and checklist aim to mitigate these risks fully.

## 12. Deployment & Rollback

- Sequence: create a preview branch with the flattened layout, set Vercel Root Directory to `.`, Build Command to `pnpm build`, deploy preview, and validate.
- Pre-cutover checklist: green `pnpm biome:check`, `pnpm type-check`, `pnpm build`, and manual smoke on the preview URL; share results in the checklist PR with two approvers.
- Production cut: schedule a low-traffic window; flip Vercel production Root Directory to `.` after preview validation; monitor logs/metrics for 30 minutes.
- Rollback: revert the Vercel Root Directory to `frontend` and redeploy the prior commit; announce rollback in the same channel.
- Communication: notify #eng-ai and on-call 24h before cut, include owners and exact timing for cutover/rollback.
