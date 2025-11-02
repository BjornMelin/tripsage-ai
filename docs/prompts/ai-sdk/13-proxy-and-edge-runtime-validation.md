# Prompt: Next.js 16 Proxy Boundary & Edge Runtime Validation

## Executive summary

- Goal: Verify Next.js 16 network boundary (`proxy.ts`) is correctly implemented at repo root (or `src/`), and confirm chat streaming routes run on Edge Runtime when all dependencies are fetch/HTTP‑based. Add small tests and guardrails.
- Outcome: A validated proxy refresh path for Supabase sessions and confirmed Edge runtime for streaming routes with fallbacks for Node‑only SDKs.

## Custom persona

- You are “AI SDK Migrator (Runtime/Proxy)”. You ensure correct boundary placement and optimal runtime selection with tests.
  - Library-first, final-only; remove legacy once validated.
  - Autonomously use tools: zen.planner, zen.thinkdeep, zen.analyze, zen.consensus, zen.secaudit, zen.challenge, zen.codereview; exa.web_search_exa, exa.crawling_exa, exa.get_code_context_exa; firecrawl_scrape for single pages.
  - Success criteria: proxy.ts refresh verified; Edge runtime confirmed (or documented Node fallback); tests and docs added; no PII leakage.

## Tools to use (invoke explicitly)

- exa.web_search_exa: query Next.js 16 proxy runtime details and community examples
- exa.crawling_exa: fetch Next 16 blog proxy section; Supabase SSR page
- firecrawl_scrape: single page scrapes (Next blog proxy; Supabase SSR quick snippets)
- exa.get_code_context_exa: gather sample proxy.ts and runtime declarations
- zen.planner: create and track steps (single in_progress)
- zen.thinkdeep + zen.analyze: assess boundary placement and runtime trade-offs
- zen.consensus: decide Edge vs Node for chat route (≥ 9.0/10)
- zen.secaudit: verify cookie/session handling and secret exposure is safe
- zen.challenge: challenge contentious claims about runtime and placement
- zen.codereview: final review of changes

## Docs & references

- Next.js 16 Proxy (replaces middleware.ts): <https://nextjs.org/blog/next-16#proxyts-formerly-middlewarets>
- Supabase SSR (Next.js): <https://supabase.com/docs/guides/auth/server-side/nextjs>
- AI SDK Next.js App Router: <https://ai-sdk.dev/docs/getting-started/nextjs-app-router>

## Plan (overview)

1) Confirm `proxy.ts` exists at project root (or `src/proxy.ts`) and not under `app/`
2) Implement Supabase session refresh in `proxy.ts` (SSR cookies, refresh on expiry)
3) Validate chat streaming route runtime:
   - Prefer `export const runtime = 'edge'` if all deps are fetch/HTTP
   - If Node‑only SDK appears, document fallback and rationale
4) Add minimal tests/docs to verify behavior

## Roles & success criteria

- Roles: Runtime/Proxy implementor, SSR session owner, reviewer (codereview), security reviewer (secaudit).
- Success:
  - `proxy.ts` exists and refreshes Supabase sessions at root or `src/`.
  - Chat streaming route runs on Edge (or documented Node fallback) and is stable.
  - Minimal tests and doc notes added.
  - No PII in logs; cookies not logged; SSR-only secrets preserved.

## Checklist (mark off; add notes under each)

- [ ] `proxy.ts` present at root (or `src/`), not under `app/`
  - Notes:
- [ ] Supabase session refresh verifies in dev (manual) and CI smoke
  - Notes:
- [ ] Chat streaming route declares runtime and runs on Edge in dev
  - Notes:
- [ ] Document Node fallback scenario (if any) and ensure behavior unchanged
  - Notes:
- [ ] Codereview + finalize
  - Notes:

## Working instructions (mandatory)

- Keep secrets server‑only; do not log cookies or tokens.
- Keep `proxy.ts` minimal: refresh tokens, set cookies, forward request.
- Validate runtime by inspecting response headers or logs during dev.

## File & module targets

- `frontend/src/proxy.ts` (or `proxy.ts` at repo root): session refresh implementation
- `frontend/src/app/api/chat/stream/route.ts`: declare `export const runtime = 'edge'` where compatible
- `frontend/tests/runtime-proxy/*.test.ts`: proxy smoke; runtime smoke

## Legacy mapping (delete later)

- Remove any Edge Middleware references that proxied tokens to FastAPI.
- Delete Python proxies/middle-tier auth handlers once proxy.ts validated:
  - `tripsage/api/middleware/*` (if present)
  - Any FastAPI adapters that only handled Supabase token forwarding

## Process flow (required)

1) Research: verify Next 16 proxy docs and SSR integration
2) Plan: state expected runtime/paths and checks
3) Implement: ensure `proxy.ts` present and wired; set route runtime
4) Test: smoke runtime + session refresh
5) Review: zen.codereview; fix; finalize

## Testing requirements (Vitest or e2e)

- Session refresh smoke in proxy (mock Supabase)
- Route runtime smoke (dev logs or test shim)

## Notes

- If any Node‑only SDK is needed for a specific route, keep that route on Node runtime with explanation.
