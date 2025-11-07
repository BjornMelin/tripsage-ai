# MCP Integration & Automation Plan (Codex Runbook)

This prompt file is a complete, actionable plan to implement and verify MCP integrations in the Tripsage AI frontend. It is designed to be executed in a fresh Codex session. It includes phased tasks with checkboxes, tool‑call guidance, code examples, and links to internal and external docs.

---

## 1) Context Snapshot
- Stack: Next.js 16 (App Router), React 19, AI SDK v6, Supabase, Upstash, Tailwind v4.
- Current MCP coverage: Next.js built‑in MCP (dev), Next DevTools MCP, Vercel MCP, Supabase MCP; optional: Playwright MCP, Upstash MCP, Browserbase/Stagehand MCP, Browser‑Use MCP, Apify MCP, AI Elements MCP.
- Integration strategy: Library‑first, minimal custom code, dev‑only exposure for sensitive tools.

---

## 2) Goals & Deliverables
- Add dev‑grade MCP wiring for IDE‑assisted workflows (diagnostics, UI guidance via AI Elements MCP, optional browser automation).
- Provide shared MCP client helper(s) and example route integration using AI SDK v6 tools.
- Verify end‑to‑end with minimal tests and clear acceptance criteria.
- Update internal docs/ADRs and map to existing AI SDK prompt tasks.

---

## 3) Prerequisites
- Node >= 20, PNPM installed.
- Frontend bootstrap done: `cd frontend && pnpm install`.
- For optional servers: credentials on hand (e.g., Browserbase API key/project ID, Apify token).

---

## 4) Quick Links (Internal)
- Setup guide: docs/developers/mcp-servers/mcp-server-setup.md
- Research brief: docs/developers/mcp-servers/dev-mcp-server-research.md
- AI Elements MCP: docs/developers/mcp-servers/ai-elements-mcp.md
- Browser automation:
  - Overview: docs/developers/mcp-servers/browser-automation/overview.md
  - Playwright MCP: docs/developers/mcp-servers/browser-automation/playwright-mcp.md
  - Browserbase MCP: docs/developers/mcp-servers/browser-automation/browserbase-mcp.md
  - Browser‑Use MCP: docs/developers/mcp-servers/browser-automation/browser-use-mcp.md
  - Apify MCP: docs/developers/mcp-servers/browser-automation/apify-mcp.md
  - Decision Matrix: docs/developers/mcp-servers/browser-automation/decision-matrix.md
- Roadmap: docs/developers/mcp-servers/research-tasks/roadmap.md

---

## 5) External References
- Next.js MCP: https://nextjs.org/docs/app/guides/mcp
- Vercel MCP: https://vercel.com/docs/mcp/vercel-mcp
- AI SDK v6 (tools): https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling
- AI SDK UI: https://ai-sdk.dev/docs/ai-sdk-ui/overview
- AI Elements MCP: https://v6.ai-sdk.dev/elements/mcp
- Next DevTools MCP: https://github.com/vercel/next-devtools-mcp
- Playwright MCP: https://github.com/microsoft/playwright-mcp
- Browserbase/Stagehand MCP: https://docs.stagehand.dev/v3/integrations/mcp/introduction
- Browser-Use MCP: https://docs.browser-use.com/customize/integrations/mcp-server
- Apify MCP: https://docs.apify.com/platform/integrations/mcp
- Upstash MCP: https://github.com/upstash/mcp-server
- Supabase MCP: https://github.com/supabase-community/supabase-mcp

---

## 6) Operating Principles (from AGENTS.md)
- Library‑first; keep custom glue minimal and deletable.
- KISS/DRY/YAGNI; remove duplication; no legacy shims.
- Dev‑only surfacing for sensitive tools; least‑privilege keys.
- Tests and docs updated; CI remains clean.

---

## 7) Tooling Guidance (Codex CLI)
- Search: `rg -n "pattern" path`, `fd -H -t f`.
- Read in chunks: `sed -n '1,200p' file`.
- Editing: `apply_patch` with minimal focused diffs.
- Plans: `update_plan` with exactly one in_progress step.
- Validation (frontend): `pnpm biome:check && pnpm type-check && pnpm test:run`.

---

## 8) Plan Overview (Phases)
- Phase A: Enable core MCPs (built‑in, Next DevTools, Vercel, Supabase) + AI Elements MCP.
- Phase B: Add shared MCP client helper and sample route integration.
- Phase C: Optional browser automation paths (Playwright MCP; Browserbase MCP; Browser‑Use MCP; Apify MCP).
- Phase D: Docs/ADR/specs and prompts mapping.
- Phase E: QA & acceptance checks.

---

## 9) Tasks & Checklists

### Phase A — MCP Enablement
- [ ] Start Next dev server for built‑in MCP: `cd frontend && pnpm dev`.
- [ ] Add Next DevTools MCP in client per mcp-server-setup.md:4.1.
- [ ] Add Vercel MCP (OAuth): mcp-server-setup.md:2.
- [ ] Add Supabase MCP (read‑only, project‑scoped): mcp-server-setup.md:3.
- [ ] Add AI Elements MCP (mcp-remote): ai-elements-mcp.md:1.

### Phase B — Shared MCP client + route integration
- [ ] Create `frontend/src/lib/mcp/client.ts` providing a factory to create MCP clients (HTTP) given a URL and optional headers.
- [ ] Add `frontend/src/lib/mcp/config.ts` to centralize known MCP endpoints (dev‑only), pulling from env vars like `AI_ELEMENTS_MCP_URL`, `PLAYWRIGHT_MCP_URL`, etc. Do not commit secrets.
- [ ] Wire example usage in a dev‑only route: `frontend/src/app/api/dev/mcp-tools/route.ts` that lists tools from AI Elements MCP and returns them as JSON.
- [ ] Integrate tools in chat stream (optional demo): in `frontend/src/app/api/chat/stream/route.ts`, demonstrate conditional tool injection when `process.env.ENABLE_MCP_TOOLS === '1'` (keep default off). Use `convertToModelMessages(messages)` and pass `tools: { ... }` incorporating wrappers around MCP tool execution.

### Phase C — Optional browser automation
- [ ] Playwright MCP for local/CI
  - [ ] Install and configure Playwright MCP in the client per browser-automation/playwright-mcp.md:1.
  - [ ] (Optional) CI job to start Playwright MCP in headless mode before test steps.
  - [ ] Add a dev route `frontend/src/app/api/dev/mcp-playwright/route.ts` to call a simple navigate tool for sanity.
- [ ] Browserbase/Stagehand MCP (managed) 
  - [ ] Export `BROWSERBASE_API_KEY` and `BROWSERBASE_PROJECT_ID`; configure per browser-automation/browserbase-mcp.md:1.
  - [ ] Decide SHTTP vs local stdio; add the remote URL (type `streamable-http`).
  - [ ] Add a dev route `frontend/src/app/api/dev/mcp-browserbase/route.ts` to run a simple navigation or extract step.
- [ ] Browser-Use MCP (local PoCs)
  - [ ] Start with `uvx browser-use --mcp` per browser-automation/browser-use-mcp.md:1.
  - [ ] (Optional) Add a dev route that calls a basic tool when the local stdio server is running.
- [ ] Apify MCP (complementary)
  - [ ] Configure OAuth or token header; per browser-automation/apify-mcp.md:1.
  - [ ] Add a dev route `frontend/src/app/api/dev/mcp-apify/route.ts` to list actors or trigger a small actor.

### Phase D — Docs/ADRs/specs & prompts mapping
- [ ] Update ADR(s) summarizing final MCP integration decisions (references to research and decision matrix).
- [ ] Cross‑check setup doc references match code paths and env var names.
- [ ] Map progress to `docs/prompts/ai-sdk/` prompts (check off where applicable):
  - [ ] 05-tools-and-mcp-integration.md — add MCP client wiring and tool injection.
  - [ ] 07-ui-ai-elements-integration.md — verify AI Elements MCP used for component references.
  - [ ] 11-testing-vitest-and-e2e.md — add Playwright MCP smoke steps if enabled.
  - [ ] 12-decommission-python-cleanup.md — list MCP-related TS migration notes.

### Phase E — QA & Acceptance
- [ ] `pnpm biome:check && pnpm type-check` clean.
- [ ] Minimal tests for the new dev routes (use Vitest; mock MCP responses). Keep these behind dev conditional or skip in CI as needed.
- [ ] Sanity run: enable AI Elements MCP in client; list tools via `GET /api/dev/mcp-tools`.
- [ ] (Optional) Sanity run: Playwright MCP navigate tool; view output.

---

## 10) Tool‑Call Templates

Search/select files:
```bash
rg -n "MCP" frontend/src | sed -n '1,200p'
fd -H -t f frontend/src/lib | sed -n '1,200p'
```

Patch file skeletons:
```json
{
  "command": [
    "bash","-lc",
    "apply_patch << 'PATCH'\n*** Begin Patch\n*** Add File: frontend/src/lib/mcp/client.ts\n+// TODO: implement createMcpClient per plan\n+export {}\n*** End Patch\nPATCH"
  ]
}
```

Plan maintenance:
```json
{
  "explanation": "Implement MCP helpers and dev routes.",
  "plan": [
    {"step": "Add MCP client helper", "status": "in_progress"},
    {"step": "Add dev routes for MCP", "status": "pending"}
  ]
}
```

---

## 11) Code Examples (reference only)

Shared MCP client (HTTP transport example):
```ts
// frontend/src/lib/mcp/client.ts
import { experimental_createMCPClient } from "ai";
import { StreamableHTTPClientTransport } from "@modelcontextprotocol/sdk/client/streamableHttp.js";

export async function createMcpClient(url: string, headers?: Record<string,string>) {
  const transport = new StreamableHTTPClientTransport(new URL(url), { requestInit: { headers } });
  return experimental_createMCPClient({ transport });
}
```

Using tools in a dev route (read-only list):
```ts
// frontend/src/app/api/dev/mcp-tools/route.ts
import { NextResponse } from "next/server";
import { createMcpClient } from "@/lib/mcp/client";

export async function GET(): Promise<Response> {
  const url = process.env.AI_ELEMENTS_MCP_URL ?? "https://registry.ai-sdk.dev/api/mcp"; // dev default
  const client = await createMcpClient(url);
  const tools = await client.tools();
  return NextResponse.json({ toolNames: Object.keys(tools ?? {}) });
}
```

Injecting tools in chat stream (dev‑guarded, conceptual):
```ts
// inside POST handler before streamText
const enable = process.env.ENABLE_MCP_TOOLS === "1";
let tools = undefined;
if (enable) {
  const mcp = await createMcpClient(process.env.AI_ELEMENTS_MCP_URL!);
  tools = await mcp.tools();
}
const result = await streamText({ model: llm, messages, tools });
```

---

## 12) Acceptance Criteria
- MCP setup verified per Phase A; AI Elements MCP reachable and listing tools.
- Shared MCP client utility present; dev routes return expected responses without secrets.
- Optional: Playwright MCP and/or Browserbase MCP demo calls succeed in dev.
- Docs and ADRs updated; prompts mapping ticked where applicable.

---

## 13) Rollback & Safety
- Keep MCP integration behind dev flags; do not expose secrets in repo.
- Remove or disable dev routes before production builds.
- If any MCP server causes instability, disable via env flags and remove client wiring.

---

## 14) Cross‑Reference Index
- Internal docs: see Section 4.
- External docs: see Section 5.

---

## 15) Session Bootstrap (suggested)
- [ ] Read Section 4 and 5 for quick context.
- [ ] Run `update_plan` with Phase A step as in_progress.
- [ ] Execute Phase A tasks; then Phase B → E.
- [ ] Keep `apply_patch` changes atomic and minimal.

```text
End of runbook.
```
