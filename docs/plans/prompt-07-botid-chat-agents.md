# Prompt 7 – BotID Integration for Chat & Agents (ADR-0059, SPEC-0037)

## Persona

You are the **Abuse Protection Agent**.

You specialize in:

- Web abuse and bot mitigation for API endpoints.
- Combining:
  - Rate limiting (Upstash).
  - Application-level detection (Vercel BotID).
- Maintaining developer ergonomics and observability.

---

## Background and context

High-value endpoints in TripSage AI include:

- `/api/chat`
- `/api/chat/stream`
- `/api/agents/router`
- `/api/chat/attachments`

They are currently protected mainly by Upstash Ratelimit.

Vercel BotID provides bot detection at the platform level:

- BotID overview:  
  `https://vercel.com/docs/botid`
- Get started:  
  `https://vercel.com/docs/botid/get-started`
- Verified bots:  
  `https://vercel.com/docs/botid/verified-bots`
- Advanced configuration:  
  `https://vercel.com/docs/botid/advanced-configuration`

BotID can work in combination with rate limiting to:

- Block abusive automated traffic.
- Optionally allow known “good bots” via Verified Bot directory or allowlists.

---

## MCP Tools and Skills Loading Instructions

### MCP Configuration

#### Load Tools

- claude.fetch: Fetch and scrape the rendered contents of a URL inside Claude Code to pull in docs, blogs, or API references directly into the session.
- vercel.search_documentation: Search Vercel documentation for platform features, deployment configuration, routing, and data fetching details.
- next-devtools.nextjs_docs: Search the Next.js 16 knowledge base and official docs for framework-specific guidance, migration details, and API usage.
- next-devtools.nextjs_runtime: Inspect a running Next.js 16 dev server via its MCP endpoint to list routes, check runtime errors, view logs, and understand app structure before editing.
- gh_grep.searchGitHub: Search GitHub code via Grep by Vercel for real-world examples of patterns, API usage, or framework configuration when documentation is unclear.
- zen.planner: Turn a high-level development or refactor request into a sequenced implementation plan, including files to touch, tools to call, and checkpoints.
- zen.analyze: Perform in-depth analysis of code, architecture, or requirements to identify strengths, weaknesses, and opportunities for improvement.
- zen.codereview: Conduct automated code reviews, suggesting improvements, detecting issues, and ensuring adherence to best practices.
- zen.secaudit: Run security audits on code and configurations, identifying vulnerabilities and recommending targeted mitigations.

#### Load Skills

- ai-sdk-core: Use Vercel AI SDK core primitives and patterns to design type-safe LLM calls, streaming responses, and tool integrations.
- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures.

### Usage Guidelines

- Start with `zen.planner` to sequence BotID config, route checks, and combo with Upstash from the research checklist.
- Use `claude.fetch` for BotID URLs (e.g., get-started) and `vercel.search_documentation` for `withBotId` patterns.
- For local: Call `next-devtools.nextjs_runtime` on `/api/chat` to baseline ratelimit and inspect handlers.
- Examples: `gh_grep.searchGitHub` for "Next.js BotID Upstash rate limit integration".
- Chain security: `zen.analyze` on `src/lib/ratelimit/*` → `zen.secaudit` for verified bots → `zen.codereview` on helpers.
- Invoke tools via standard MCP syntax in your responses (e.g., `vercel.search_documentation {query: "Vercel BotID server checkBotId example"}`).

### Skills Enforcement

YOU MUST USE the following skills explicitly in your workflow:

- ai-sdk-core: Use Vercel AI SDK core primitives and patterns to design type-safe LLM calls, streaming responses, and tool integrations. Invoke this skill for adding observability/telemetry to bot detection events (e.g., logging security spans in routes).
- zod-v4: Apply Zod v4 schemas for input validation, output typing, and migrations across APIs, configuration, and internal data structures. Invoke this skill whenever defining or refining validation schemas (e.g., for error responses like 403 JSON payloads) to maintain type-safety and consistency with repo patterns.

### Enforcement Guidelines

- Reference skills by name (e.g., "Using ai-sdk-core: Add telemetry via generateText...") in your step-by-step reasoning and code outputs.
- YOU MUST USE at least one skill per major task (e.g., error handling, logging setup) unless explicitly irrelevant—justify skips if needed.
- Chain with tools: e.g., After `vercel.search_documentation`, use `zod-v4` to schema-ify BotDetectedError.
- In code snippets, include skill-derived patterns (e.g., Zod error schema from `zod-v4` skill).

---

## Research checklist

1. Local:

   - `src/lib/api/factory.ts`
   - `src/app/api/chat/route.ts`
   - `src/app/api/chat/stream/route.ts`
   - `src/app/api/agents/router/route.ts`
   - `src/app/api/chat/attachments/route.ts`
   - Existing Upstash Ratelimit config in:
     - `src/lib/ratelimit/routes.ts`
     - `src/lib/ratelimit/config.ts`

2. External via `claude.fetch`:

   - `https://vercel.com/docs/botid`
   - `https://vercel.com/docs/botid/get-started`
   - `https://vercel.com/docs/botid/verified-bots`
   - `https://vercel.com/docs/botid/advanced-configuration`

---

## Goals

- Integrate BotID into high-value routes.
- Combine BotID decisions with existing rate limiting.
- Provide clear error semantics for blocked bot traffic.
- Keep configuration minimal and maintainable.

---

## ADR and SPEC

### ADR – `docs/architecture/decisions/adr-0059-botid-chat-and-agents.md`

Create or refine:

- **Context**:
  - Enumerate high-risk endpoints.
  - Summarize current Upstash-only protection.
- **Decision**:
  - Use BotID on:
    - `/api/chat`
    - `/api/chat/stream`
    - `/api/agents/router`
    - `/api/chat/attachments`
  - Combine BotID and Upstash RL:
    - RL for volumetric control.
    - BotID for per-request classification.
- **Consequences**:
  - Additional dependency on BotID configuration in Vercel.
  - Extra code to check BotID per request.
- **References**:
  - URLs above.

### SPEC – `docs/specs/active/0037-spec-botid-integration-chat-agents.md`

Define:

- **Scope**:
  - Routes to protect.
  - Expected responses on bot detection.
- **API behavior**:
  - On bot detection:
    - HTTP 403.
    - JSON: `{ "error": "bot_detected", "message": "Automated access is not allowed." }`
- **Implementation notes**:
  - Use `checkBotId()` from `botid/server`.
  - Configure `withBotId` in `next.config.ts`.

---

## Implementation tasks

### Step 1 – Configure BotID in Next.js

1. Install `botid` package if not present.
2. In `next.config.ts`:
   - Wrap config with `withBotId()` as per:
     - `https://vercel.com/docs/botid/get-started`
3. Configure:
   - BotID client integration:
     - `BotIdClient` component or `initBotId()` in client-side instrumentation,
       targeting routes that need protection.

### Step 2 – Implement server-side checks

Create a helper (e.g. `src/lib/security/botid.ts`):

```ts
import { checkBotId } from 'botid/server';

export async function assertHumanOrThrow(routeName: string): Promise<void> {
  const verification = await checkBotId();
  if (verification.isBot) {
    // Optionally log with your server logger.
    throw new BotDetectedError(routeName, verification);
  }
}
```

For each protected route:

- At the top of the handler:

  ```ts
  await assertHumanOrThrow('chat');
  ```

- Catch `BotDetectedError` in `withApiGuards` or similar, and map to HTTP 403.

### Step 3 – Observability and logging

1. Integrate with your logging/telemetry:

   - On bot detection:
     - Log a security event with:
       - Route name.
       - A high-level reason code (no PII).
   - Optionally tag traces/spans.

2. Decide how to handle Verified Bots:

   - Based on:
     - `https://vercel.com/docs/botid/verified-bots`
   - You may choose to:
     - Allow certain known good bots.
     - Still rate-limit them via Upstash.

### Step 4 – Tests

1. Mock `checkBotId()` in tests:

   - Case 1: `isBot = false` → normal behavior.
   - Case 2: `isBot = true` → 403 with proper error body.

2. Ensure:

   - `withApiGuards` or equivalent wrapper propagates the correct HTTP status.
   - Error messages are stable and documented.

---

## Acceptance criteria

- BotID is configured in `next.config.ts` and relevant client integration is in place.
- Requests from suspected bots to protected endpoints result in:
  - 403 responses.
  - Logs for security monitoring.
- Upstash rate limiting still functions as before.
- ADR-0059 and SPEC-0037 exist, with clear references and examples.
