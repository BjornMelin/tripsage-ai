# Tools & MCP Inventory

This document describes which tools are available in this Codex environment and how we verify changes.

## MCP Servers / Tooling (observed)

### Next.js DevTools MCP

- `init` called successfully for this repo (required at session start).
- Documentation lookup available via `nextjs_docs` (`search`/`get`).
- Runtime diagnostics confirmed working:
  - `nextjs_index` (server discovery)
  - `nextjs_call` (runtime tools on a dev server)
  - `browser_eval` (Playwright-driven browser automation)

Official docs index URL: https://nextjs.org/docs/llms.txt

### Browser automation (verification)

- **Preferred** in this repo/harness: Next DevTools `browser_eval`.
- Confirmed `browser_eval` browser enum values: `chrome`, `firefox`, `webkit`, `msedge` (note: `chromium` is rejected).
- Keep verification steps deterministic and accessibility-driven (navigate → snapshot → interact → snapshot).

### Context7 (library docs)

- Use `resolve-library-id` then `query-docs`.

### Supabase Docs (GraphQL search)

- Use `supabase.search_docs` for SSR auth, RLS, storage, realtime, edge functions.

### Exa (web discovery)

- Use `exa.web_search_exa` / `exa.deep_search_exa` / `exa.crawling_exa`.

### Grep MCP (GitHub search)

- Use `gh_grep.searchGitHub` for real-world patterns and edge cases.

### shadcn/ui registry tools

- `shadcn.get_project_registries` confirmed `@shadcn` registry is configured for this repo.
- Use `shadcn.search_items_in_registries` + `shadcn.get_item_examples_from_registries` to avoid custom UI reinvention.

## Verification Defaults

- Build: `pnpm build`
- Types: `pnpm type-check`
- Tests: `pnpm test:affected`
- Browser validation: `next-devtools.browser_eval` flows documented per task.
- E2E suite: `pnpm test:e2e` (runs all configured browser projects; may require `pnpm exec playwright install`)
