# Deployment Runbook: Vercel + Supabase + Upstash

This repository uses Vercel CLI prebuilt deployments as the authoritative
production path. Git deployments are disabled in `vercel.json`, so a production
deployment is not complete until GitHub Actions runs `vercel build --prod`,
deploys the prebuilt artifact with `vercel deploy --prebuilt --prod
--skip-domain`, passes smoke checks against the emitted deployment URL, and then
promotes that verified deployment with `vercel promote`.

Issue #733 supersedes the broad placeholder direction in #233 for the web app
deployment path. Keep #233 only for remaining infrastructure work that is not
covered by this Vercel CLI runbook.

## Required GitHub Environment Secrets

Configure these in each GitHub environment that can run `.github/workflows/deploy.yml`:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_PROJECT_ID`

The workflow fails before deploy if any are missing. These values are used only
by the Vercel CLI and must not be printed in logs.

## Required Vercel Production Environment

Production deploys run `pnpm deploy:check-env` inside
`vercel env run -e production`, so the following variables must exist in the
Vercel project production environment:

- Origin:
  - A valid HTTPS origin in one of `APP_BASE_URL`, `NEXT_PUBLIC_SITE_URL`,
    `NEXT_PUBLIC_BASE_URL`, or `NEXT_PUBLIC_APP_URL`
  - `NEXT_PUBLIC_SITE_URL` as a valid HTTPS origin while QStash enqueue code
    uses it for callback URL construction
- Supabase:
  - `NEXT_PUBLIC_SUPABASE_URL`
  - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` preferred, or
    `NEXT_PUBLIC_SUPABASE_ANON_KEY` as legacy fallback
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `SUPABASE_JWT_SECRET`
- Webhook and telemetry:
  - `HMAC_SECRET`
  - `TELEMETRY_HASH_SECRET`
- Upstash Redis and QStash:
  - `UPSTASH_REDIS_REST_URL`
  - `UPSTASH_REDIS_REST_TOKEN`
  - `QSTASH_TOKEN`
  - `QSTASH_CURRENT_SIGNING_KEY`
  - `QSTASH_NEXT_SIGNING_KEY`
- AI provider contract:
  - If `ENABLE_AI_DEMO=true`, at least one of `AI_GATEWAY_API_KEY`,
    `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, or
    `XAI_API_KEY`

Use Vercel project environment variables for app secrets. Do not mirror app
provider secrets into GitHub unless a separate GitHub-hosted task explicitly
requires them.

## Production Deploy Flow

1. Trigger the Deploy workflow with `environment=production`.
2. GitHub Actions validates `VERCEL_TOKEN`, `VERCEL_ORG_ID`, and
   `VERCEL_PROJECT_ID`.
3. The workflow installs pinned `pnpm` and Vercel CLI versions.
4. The workflow runs `vercel pull --yes --environment=production`.
5. The workflow runs production env contract checks with:
   `vercel env run -e production -- pnpm deploy:check-env -- --environment production`.
6. The workflow runs live Supabase and Upstash probes with:
   - `vercel env run -e production -- pnpm ops infra check supabase`
   - `vercel env run -e production -- pnpm ops infra check upstash`
7. The workflow builds the Vercel artifact with:
   `vercel build --prod --token=$VERCEL_TOKEN`.
8. The workflow deploys the local build output without moving production
   domains yet:
   `vercel deploy --prebuilt --prod --skip-domain --archive=tgz --yes --token=$VERCEL_TOKEN`.
9. The workflow runs `pnpm deploy:smoke` against the emitted deployment URL.
10. After smoke checks pass, the workflow promotes the verified production
    deployment with `vercel promote <deployment-url> --yes --timeout=5m`.
11. After promotion succeeds, the workflow writes `deployment-summary.json`,
    uploads it as an artifact, and updates the GitHub deployment status with
    the real deployment URL.

The workflow must fail if no Vercel deployment URL is produced.

## Smoke Coverage

`pnpm deploy:smoke -- --url <deployment-url> --environment production` verifies:

- Public app shell returns HTML.
- `/api/health` returns a no-store JSON health payload.
- `/auth/me` rejects unauthenticated requests with `401`.
- `/login?redirect_url=%2Fdashboard` renders an HTML shell for auth redirects.
- `/api/keys/validate` rejects unauthenticated BYOK validation requests. This
  is a route-guard smoke check, not an authenticated provider health check.
- QStash job routes reject unsigned POST requests with `401` after environment
  validation has already confirmed the signing-key variables are present:
  - `/api/jobs/attachments-ingest`
  - `/api/jobs/memory-sync`
  - `/api/jobs/notify-collaborators`
  - `/api/jobs/rag-index`

The smoke script prints a JSON summary and exits non-zero on failure. It never
prints provider tokens or secret values.

Authenticated BYOK/provider lifecycle health remains owned by #735.

`staging` and `development` workflow inputs use Vercel Preview environment
settings. Add `--target=<custom-environment>` only after the Vercel project has
a named custom environment and corresponding environment-variable contract.

## Rollback

Use the Vercel CLI rollback command from a trusted workstation with audited
Vercel access:

```bash
vercel rollback --token "$VERCEL_TOKEN"
```

To roll back to a specific deployment:

```bash
vercel rollback <deployment-id-or-url> --token "$VERCEL_TOKEN"
```

After rollback, run:

```bash
vercel rollback status [project] --token "$VERCEL_TOKEN"
pnpm deploy:smoke -- --url <rolled-back-url> --environment production
```

If the rollback target is unknown, inspect recent production deployments:

```bash
vercel list --prod --token "$VERCEL_TOKEN"
vercel inspect <deployment-url> --token "$VERCEL_TOKEN"
```

## Manual Local Verification

Before changing deployment behavior, run the local checks that do not require
production secrets:

```bash
pnpm biome:fix
pnpm type-check
pnpm test:affected
```

Run the production contract check only inside a populated environment, or with
local dummy values that preserve shape without exposing real secrets:

```bash
pnpm deploy:check-env -- --environment production
```

This command intentionally fails unless production-like environment variables
are present. Use it as a contract check, not as a secret bootstrap mechanism.

## References

- Vercel CLI deploy docs: https://vercel.com/docs/cli/deploy
- Vercel CLI build docs: https://vercel.com/docs/cli/build
- Vercel CLI env docs: https://vercel.com/docs/cli/env
- Vercel CLI promote docs: https://vercel.com/docs/cli/promote
- Vercel CLI rollback docs: https://vercel.com/docs/cli/rollback
- Vercel production deployments: https://vercel.com/docs/deployments/production-deployments
- Supabase Next.js quickstart: https://supabase.com/docs/guides/getting-started/quickstarts/nextjs
- BotID docs: https://vercel.com/docs/botid/get-started
