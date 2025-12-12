---
title: Dependency Deprecations
status: active
last_updated: 2025-12-12
---

This repo aims to keep `pnpm install` free of deprecated subdependency noise **without** using risky, broad `pnpm.overrides` for native/build chains. We prefer upstream upgrades and explicit peer management.

## Baseline (2025-12-12)

`pnpm install` reported deprecated subdependencies:

### Cluster A — Native build toolchain via `mem0ai` peers

Root:

`mem0ai` peers → auto-installed `sqlite3@5.1.7` → `node-gyp@8.x` → legacy npm tooling

Deprecated packages:

- `@npmcli/move-file@1.1.2`
- `npmlog@6.0.2`
- `are-we-there-yet@3.0.1`
- `gauge@4.0.4`
- `glob@7.2.3`
- `inflight@1.0.6`
- `rimraf@3.0.2`

These are **install/build-only**, not runtime dependencies for TripSage. They only appear because pnpm auto-installs unused peers for `mem0ai`.

### Cluster B — `streamdown` Markdown stack

Root:

`streamdown@1.6.x` → `hast@1.x` (deprecated; renamed to `rehype`).

We keep Streamdown for streaming UX, CJK emphasis correctness, and built‑in Shiki/controls.

### Cluster C — Fetch/FormData polyfills

Root:

AI/SDK peers (when auto-installed) → `formdata-node@4.4.1` / `fetch-blob` → `node-domexception@1.0.0` (deprecated in favor of platform `DOMException`).

### Cluster D — Release tooling

Root:

`semantic-release@25` → `semver-diff@5` (deprecated; semver includes diff now).

## Current State After Resolution (2025-12-12)

After applying the strategy below (disable auto peer installs, restore pnpm peer rules, and add missing peers), `pnpm install` no longer surfaces Clusters A or most of C. The dependency tree still contains only upstream‑blocked deprecations:

- `hast@1.0.0` (via `streamdown@1.6.x`)
- `node-domexception@1.0.0` (polyfill chain; unused directly in app)
- `semver-diff@5.0.0` (via `semantic-release@25`)

We accept these until upstreams ship non‑deprecated replacements, per "Keep Streamdown" and pinned AI SDK constraints.

## Override Pins (Security)

We keep two narrow `pnpm.overrides` for security advisories. `pnpm` does not support inline override comments, so rationale lives here.

- `axios@1.13.2`: pinned to pick up CVE‑2025‑58754 (DoS via `data:` URL) and CVE‑2025‑27152 fixes. Added 2025‑12‑11 by Bjorn Melin. Verified with `pnpm why axios` (only `mem0ai` depends on it) and `pnpm audit` clean.
- `undici@5.29.0`: pinned for CVE‑2025‑47279 fix. Added 2025‑12‑11 by Bjorn Melin. Verified with `pnpm why undici` (only `semantic-release` tooling chain) and `pnpm audit` clean.

## Resolution Strategy

1. **Prune unused `mem0ai` peers (Cluster A + most of C)**  
   - Disable pnpm auto peer install.
   - Ignore missing peers that are not used in hosted Mem0 mode.
   - Verify Mem0 hosted client works without `sqlite3`.

2. **Keep Streamdown and track upstream (Cluster B)**  
   - No local override; wait for upstream migration off `hast`.
   - Maintain Tailwind v4 scanning + centralized config in app.

3. **Accept upstream‑blocked deprecations (residual C/D)**  
   - AI SDK versions are pinned by repo contract.
   - `semantic-release` is already at latest in this repo.

## Upstream Tracking

- Streamdown `hast` deprecation: track migration issue in `vercel/streamdown` repo.
- Mem0 peers optionality: request upstream to mark storage peers optional.
- AI SDK polyfills: re-check when contract allows bumping pinned betas.

## Recheck Cadence

Quarterly dependency hygiene:

- Re-run `pnpm install` and confirm deprecation list.
- Prefer upstream bumps; avoid new overrides unless a CVE requires a short‑lived pin.
