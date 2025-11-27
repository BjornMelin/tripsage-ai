# API Key Route Migration Notice (October 28, 2025)

All API key administration traffic has moved from `/api/user/keys` to `/api/keys`.

## What Changed

- Next.js route handlers now serve `/api/keys` only. The former `/api/user/keys` paths return `404`.
- Frontend hooks (`useApiKeys`, `useAddApiKey`, `useDeleteApiKey`, `useValidateApiKey`) and Vitest coverage were updated to the new base path.
- Operator documentation (security guide, admin guide) and API usage examples reference the new endpoints.

## Action Required

1. **Client updates** – Audit any first- or third-party clients, SDKs, or automation scripts that still call `/api/user/keys`. Update them to `/api/keys` before the next deploy window.
2. **Network allowlists** – Refresh ingress/WAF/firewall rules that match on the old path to ensure `/api/keys` remains permitted.
3. **Monitoring & alerts** – Point synthetic checks, dashboards, and alerting rules to `/api/keys/metrics` and `/api/keys/audit`.
4. **Rollout verification** – During the first deploy after this change, confirm the readiness probe reports `authentication: true` and that admin gating behaves as expected.

## Communication Template

```text
Subject: ACTION REQUIRED – TripSage API key endpoints moved to /api/keys

We have completed the migration of API key endpoints from /api/user/keys to /api/keys.

What you need to do:
  • Update any callers that reference /api/user/keys (list, create, validate, rotate, delete) to use /api/keys.
  • Refresh ingress/WAF rules or service meshes that permit the old path so /api/keys traffic is allowed.
  • Update dashboards, synthetic monitors, or alerts that hit /api/user/keys/metrics or /api/user/keys/audit to the new /api/keys equivalents.

The old paths now return 404. Please complete these updates before the next production deployment window.

Thanks,
TripSage Platform Team
```

## Tracking

- Changelog: see the [Unreleased](../../CHANGELOG.md#unreleased) section.
- Related tests: `frontend/src/hooks/__tests__/use-api-keys.test.ts`
