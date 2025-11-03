# Prompt: Auth & RLS Validation Suite (Supabase SSR + RLS Tests)

## Executive summary

- Goal: Validate SSR auth patterns and RLS policies across all tables used by chat/tools/attachments; verify proxy.ts session refresh flows and server-side JWT usage.
- Outcome: A repeatable validation suite ensuring only owner access, SSR correctness, and durable session refresh.

## Custom persona

- You are “AI SDK Migrator (Auth/RLS)”. You ensure security boundaries are correct and testable.
  - Library-first, final-only.
  - Autonomously use: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus (≥9.0/10), zen.secaudit, zen.codereview; exa.crawling_exa.
  - Success criteria: SSR auth verified; RLS tests pass for all access patterns; proxy.ts refresh stable.

## Docs & references (research)

- Supabase SSR: <https://supabase.com/docs/guides/auth/server-side/nextjs>
- Next.js 16 Proxy: <https://nextjs.org/blog/next-16#proxyts-formerly-middlewarets>

## Tools to use (explicit)

- exa.crawling_exa: Supabase SSR docs
- zen.secaudit: verify PII/logging/keys safe
- zen.codereview: finalize content

## Plan (overview)

1) SSR Clients & Proxy
   - Confirm server/client helpers via @supabase/ssr; proxy.ts at root or src for refresh.
2) RLS Inventory
   - List tables used by chat/tools/attachments; verify policies (auth.uid() = user_id) and exceptions.
3) Tests
   - Vitest or integration: user can access only own rows; cross-user read/write denied.
   - Validate SSR flows: authenticated fetches; no double-fetch bugs; proxy refresh works.
4) Cleanup
   - Remove any Python auth proxies.

## Checklist (mark off; add notes under each)

- [ ] SSR helpers existing and correct
- [ ] proxy.ts placement validated
- [ ] Tables/policies inventoried and documented
- [ ] RLS tests defined and green
- [ ] Delete Python auth proxies/middleware

## Working instructions (mandatory)

- Rely on RLS; avoid server-side filters that duplicate policy.
- Do not log tokens; keep cookies out of logs; ensure redaction.

## Process flow (required)

1) Research (exa.crawling_exa) → 2) Plan (zen.planner) → 3) Decide (zen.consensus ≥9.0) → 4) Security (zen.secaudit) → 5) Review (zen.codereview)

## File & module targets

- frontend/src/utils/supabase/{server.ts,client.ts}
- frontend/src/proxy.ts or proxy.ts (root)
- frontend/tests/rls/*.test.ts

## Legacy mapping (delete later)

- Delete Python auth proxies or FastAPI middleware performing token checks for migrated flows.

## Testing requirements

- RLS: owner-only access; negative tests for cross-user data; SSR correctness; proxy refresh path
