# TripSage Frontend Resume Prompt (Next.js 16 · Node 24 · Supabase SSR · AI SDK v5 · Tailwind v4)

Use this prompt in a new session to regain full context, including what is complete, what remains, and how to operate the MCP tools. Paste everything between the lines into the new session.

---

You are resuming the TripSage frontend modernization. Load the files listed, then follow the phases and checklists.

Context files to load (open these first)
- docs/adrs/README.md
- docs/adrs/adr-0013-adopt-next-js-16-proxy-and-async-apis-deprecate-middleware.md
- docs/adrs/adr-0014-migrate-supabase-auth-to-supabase-ssr-and-deprecate-auth-helpers-react.md
- docs/adrs/adr-0015-upgrade-ai-sdk-to-v5-ai-sdk-react-and-usechat-redesign.md
- docs/adrs/adr-0016-tailwind-css-v4-migration-css-first-config.md
- docs/adrs/adr-0017-adopt-node-js-v24-lts-baseline.md
- docs/adrs/adr-0018-centralize-supabase-typed-helpers-for-crud.md
- docs/specs/spec-next16-migration.md
- docs/specs/spec-supabase-ssr-typing.md
- docs/specs/spec-ai-sdk-v5.md
- docs/specs/spec-tailwind-v4.md
- docs/specs/spec-zod-v4-migration.md
- CHANGELOG.md

App config and routes
- frontend/next.config.ts
- frontend/src/proxy.ts
- frontend/src/app/auth/confirm/route.ts
- frontend/src/app/api/chat/route.ts
- frontend/src/app/api/chat/attachments/route.ts
- frontend/src/hooks/use-chat-ai.ts
- frontend/src/components/features/chat/messages/message-bubble.tsx
- frontend/src/components/features/chat/messages/message-item.tsx

Supabase + repositories
- frontend/src/lib/supabase/client.ts
- frontend/src/lib/supabase/server.ts
- frontend/src/lib/supabase/database.types.ts
- frontend/src/lib/supabase/typed-helpers.ts
- frontend/src/lib/repositories/trips-repo.ts

Stores (notably trips)
- frontend/src/stores/trip-store.ts

Redis helper
- frontend/src/lib/redis.ts

Project state (what’s done)
- Next 16 Cache Components enabled; proxy.ts replaces middleware; SSR audit captured in docs/specs/spec-next16-migration.md.
- Native AI SDK v5 chat route streams UI messages (frontend/src/app/api/chat/route.ts); client UI renders message.parts.
- Supabase SSR utilities + typed CRUD helpers; auth confirmation route present.
- Tailwind v4 CSS-first config verified.
- Biome zero diagnostics on touched files; TypeScript type-check clean; attachments route tests passing.

Open items (track in zen.planner)
- Backend alignment audit (FastAPI chat vs native route) — keep FastAPI chat for non-frontend consumers; attachments remain on FastAPI.
- Optional: AI tool parts UI enhancements + tests.
- Zod v4 branch work per spec-zod-v4-migration.md (defer if not needed now).

Phases and checklists
1) SSR/caching/tagging
- [x] cookies() before Supabase auth in server handlers
- [x] cache tag revalidation after attachments writes (revalidateTag('attachments','max'))
- [ ] Add tags to future server actions and document in spec-next16-migration.md

2) Supabase typed CRUD
- [x] Central helpers in typed-helpers.ts used by hooks and repo
- [ ] Add/expand smoke tests for repo mapping if you modify schemas

3) AI SDK v5 tooling (optional)
- [ ] Add demo tool with inputSchema and stopWhen (route already supports a confirm tool)
- [ ] Render tool-* parts in UI + tests

Validation commands
- Node 24 LTS required (see .nvmrc/.node-version); pnpm 10+
- cd frontend && pnpm biome:check --write && pnpm type-check && pnpm build && pnpm test -t attachments -- --run
- Python: source .venv/bin/activate && uv run pyright (strict) && ruff format . && ruff check . --fix && pytest (for backend portions you touch)

MCP tool usage (concise)
- exa.get_code_context_exa: fetch usage examples for library APIs before coding
- exa.web_search_exa: confirm latest doc changes (Next 16, Tailwind v4, AI SDK v5)
- exa.crawling_exa: extract specific doc pages for ADR/spec citations
- zen.planner: keep single plan; one step in_progress at all times
- zen.codereview: run after each patch set; fix high/critical before merging
- zen.analyze: architecture/SSR/caching audits
- zen.secaudit: auth/headers/cookies/Redis checks
- zen.consensus: make proxy vs native route decisions explicit if revisited

Links (reference)
- Next 16 upgrade: https://nextjs.org/docs/app/guides/upgrading/version-16
- Proxy reference: https://nextjs.org/docs/app/api-reference/file-conventions/proxy
- revalidateTag: https://nextjs.org/docs/app/api-reference/functions/revalidateTag
- Next 16 blog: https://nextjs.org/blog/next-16
- Supabase SSR (Next): https://supabase.com/docs/guides/auth/server-side/nextjs
- AI SDK v5: https://ai-sdk.dev/docs/migration-guides/migration-guide-5-0
- Tailwind v4: https://tailwindcss.com/docs/upgrade-guide

---

End of resume prompt.

