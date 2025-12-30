---
title: Dependency Deprecations
status: active
last_updated: 2025-12-30
---

This repo aims to keep `pnpm install` free of deprecated subdependency noise **without** using risky, broad `pnpm.overrides` for native/build chains. We prefer upstream upgrades and explicit peer management.

## Baseline (2025-12-30)

`pnpm install` reports minimal deprecated subdependencies after removing `mem0ai`.

### Cluster A — Resolved (mem0ai removed)

**Status: RESOLVED** — `mem0ai` was removed in v1.22.6 (2025-12-30). Semantic search is now handled natively by Supabase pgvector via `match_turn_embeddings` RPC.

The following deprecated packages are no longer in the dependency tree:

- `@npmcli/move-file@1.1.2`
- `npmlog@6.0.2`
- `are-we-there-yet@3.0.1`
- `gauge@4.0.4`
- `rimraf@3.0.2`

### Cluster B — `streamdown` Markdown stack

Root:

`streamdown@1.6.x` → `hast@1.x` (deprecated; renamed to `rehype`).

We keep Streamdown for streaming UX, CJK emphasis correctness, and built‑in Shiki/controls.

### Cluster C — Fetch/FormData polyfills

Root:

AI/SDK peers (when auto-installed) → `formdata-node@4.4.1` / `fetch-blob` → `node-domexception@1.0.0` (deprecated in favor of platform `DOMException`).

> **Note**: With `mem0ai` removed, the `node-domexception` chain is significantly reduced.

### Cluster D — Release tooling

Root:

`semantic-release@25` → `semver-diff@5` (deprecated; semver includes diff now).

## Current State After Resolution (2025-12-30)

After removing `mem0ai` and switching to native Supabase pgvector for semantic search, `pnpm install` no longer surfaces Cluster A. The dependency tree still contains only upstream-blocked deprecations:

- `glob@7.2.3` (via `madge` dev dependency)
- `inflight@1.0.6` (via `glob` child)
- `hast@1.0.0` (via `streamdown@1.6.x`)
- `semver-diff@5.0.0` (via `semantic-release@25`)

We accept these until upstreams ship non-deprecated replacements, per "Keep Streamdown" and dev tooling constraints.

## Override Pins (Security)

We keep narrow `pnpm.overrides` for security advisories. `pnpm` does not support inline override comments, so rationale lives here.

- `axios@1.13.2`: kept for potential transitive dependencies. Original pin was for `mem0ai` (now removed).
- `undici@5.29.0`: pinned for [CVE‑2025‑47279](https://alas.aws.amazon.com/cve/html/CVE-2025-47279.html) (webhook retry memory leak). Added 2025‑12‑11 by Bjorn Melin. Verified with `pnpm why undici` (only `semantic-release` tooling chain) and `pnpm audit` clean.
- `prismjs@>=1.30.0`: security advisory compliance.
- `brace-expansion@>=2.0.2`: security advisory compliance.

## Resolution Strategy

1. **Remove `mem0ai` (Cluster A) — DONE**
   - Replaced with native Supabase pgvector semantic search via `match_turn_embeddings` RPC.
   - Eliminates 19 optional peer dependencies and external API calls.

2. **Keep Streamdown and track upstream (Cluster B)**
   - No local override; wait for upstream migration off deprecated `hast`, while keeping Tailwind v4 scanning + centralized config in app.

3. **Accept upstream-blocked deprecations (residual C/D)**
   - `glob`/`inflight` via `madge` dev dependency.
   - `semantic-release` is already at repo-latest.

## Upstream Tracking

- Streamdown `hast` deprecation: track upstream migration in `vercel/streamdown` ([issues search](https://github.com/vercel/streamdown/issues?q=hast+deprecation)).
- Madge `glob` deprecation: track upstream migration in `pahen/madge` ([issues search](https://github.com/pahen/madge/issues?q=glob)).

## Recheck Cadence

Quarterly dependency hygiene:

- Re-run `pnpm install` and confirm deprecation list.
- Prefer upstream bumps; avoid new overrides unless a CVE requires a short‑lived pin.
