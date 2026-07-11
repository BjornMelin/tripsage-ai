# SPEC-0110: Deployment on Vercel (Supabase + Upstash)

**Version**: 1.3.0
**Status**: Final
**Date**: 2026-07-09

## Goals

- Deterministic Vercel CLI deploys using prebuilt artifacts and explicit promotion.
- Safe secret handling.
- Repeatable feature-aware environment validation.

For operational runbooks (monitoring, alerting, incident response, secret rotation), see [Deployment Runbook](../../runbooks/deployment-vercel.md).

## Non-goals

- Self-hosted infrastructure (Vercel is the canonical platform).
- Providing production runbooks for incident response or scaling (see [Deployment Runbook](../../runbooks/deployment-vercel.md)).
- Supporting multiple deployment platforms (Vercel is the standardized target).

## Requirements

- Vercel Project configured with:
  - Git deployments disabled; `.github/workflows/deploy.yml` owns build, smoke,
    and promotion.
  - Supabase integration (env vars)
  - Upstash integration (env vars)
  - BotID (Vercel's bot detection) enabled for configured routes (see [ADR-0059](../../architecture/decisions/adr-0059-botid-chat-and-agents.md))
  - Proxy enabled via `src/proxy.ts` (CSP nonce + baseline security headers + Supabase SSR cookie refresh)

- Environment validation:
  - Runtime schema: `src/domain/schemas/env.ts`
  - Deploy gate: `scripts/verify-production-env.mjs`
  - Fails fast on missing/invalid production secrets before build/deploy.

- Production provenance:
  - Gate: `scripts/verify-deploy-provenance.mjs`
  - Runs before deployment secrets are read.
  - Requires `refs/heads/main`, the live default-branch head SHA, and a completed
    successful CI workflow run for that exact SHA.
  - Repeats immediately before production promotion so a candidate cannot be
    promoted after main advances during build or smoke verification.
  - Applies equally to manually dispatched and reusable workflow calls.
  - Requires the GitHub `Production` environment to allow only the selected
    branch `main`.

- Required environment groups:
  - Core origins: `APP_BASE_URL`, public app/API/site URLs, and CSP report origin.
  - Supabase: project URL, publishable key, service role key, JWT secret, and Vault RPC support.
  - Security: `HMAC_SECRET`, `MFA_BACKUP_CODE_PEPPER`,
    `TELEMETRY_HASH_SECRET`, and `BYOK_HEALTHCHECK_KEY`.
  - Upstash: Redis REST credentials, QStash token, and QStash signing keys.
  - Feature-aware providers: Stripe, Resend, and Amadeus require complete
    variable groups when configured. AI demo mode requires telemetry plus at
    least one valid configured AI provider key.

- Activation telemetry operations:
  - Configure an OpenTelemetry trace drain/exporter before using activation events for
    production aggregation. The live Vercel environment does not configure one.
  - Count activated planners as unique `user.id_hash` values on
    `activation.trip_created`; treat `activation.itinerary_item_completed` as the
    deeper conversion milestone.
  - Keep monetization disabled until production evidence reaches both 500 activated
    planners and 30 explicit paid-feature requests.
  - Never export raw user, trip, or itinerary-item identifiers or content. Identifier
    attributes depend on `TELEMETRY_HASH_SECRET` and are omitted when unavailable.

## Environment setup

1) Link the repository to a Vercel project, but keep Vercel Git deployments disabled.
2) Restrict the GitHub `Production` environment deployment policy to `main`.
3) Ensure the live main head has a completed successful CI run.
4) Configure Supabase and Upstash integrations or set equivalent env vars manually.
5) Enable BotID for the routes described in ADR-0059.
6) Run `pnpm deploy:check-env`.
7) Build with `vercel build --prod`.
8) Deploy the prebuilt artifact with `vercel deploy --prebuilt --prod --skip-domain`.
9) Run `pnpm deploy:smoke -- --url "$DEPLOYMENT_URL"`.
10) Promote with `vercel promote "$DEPLOYMENT_URL" --yes --timeout=5m`.

Notes:

- Nonce-based CSP (via Proxy) requires request-time values for inline scripts/styles. With Cache Components enabled, keep Dynamic API access (e.g. `headers()`) inside `<Suspense>` boundaries so PPR can stream dynamic content without blocking the build.
- Many sensitive routes fail-closed when Upstash is unavailable; ensure Upstash env vars are configured for preview + production.

## References

```text
Next.js on Vercel: https://vercel.com/docs/frameworks/full-stack/nextjs
Vercel docs: https://vercel.com/docs
Supabase Next.js quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
Upstash: https://upstash.com/docs
Deployment Runbook: ../../runbooks/deployment-vercel.md
Environment Validation Schema: ../../../src/domain/schemas/env.ts
Production Provenance Gate: ../../../scripts/verify-deploy-provenance.mjs
```
