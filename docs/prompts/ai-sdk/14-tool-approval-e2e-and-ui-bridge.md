# Prompt: Tool Approvals E2E (Server + UI Bridge)

## Executive summary

- Goal: Implement and validate end-to-end tool approval flow using AI SDK v6 tools and the AI SDK UI Chatbot tool-usage pattern. Ensure the server pauses for approval and the UI provides a confirmation UX.
- Outcome: A working approval flow, tests, and UX hooks wired to `addToolApprovalResponse` (or current equivalent) with UNVERIFIED property names noted.

## Custom persona

- You are “AI SDK Migrator (Tool Approvals)”. You ensure safe, clear user interaction for sensitive tools.

## Docs & references

- Chatbot Tool Usage: <https://ai-sdk.dev/docs/ai-sdk-ui/chatbot-tool-usage>
- Tool Calling: <https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling>

## Plan (overview)

1) Define at least one sensitive tool with approval required
2) Update streaming chat route to pass tools and handle approval pause/resume semantics
3) Update UI to surface an approval prompt and send the approval response
4) Add tests (unit/integration/UI) covering pause/resume and final result

## Checklist (mark off; add notes under each)

- [ ] Sensitive tool defined in server registry (UNVERIFIED approval property name; follow docs pattern)
  - Notes:
- [ ] Chat route wires tools with approval flow; pause/resume works
  - Notes:
- [ ] UI surfaces approval prompt and sends approval response
  - Notes:
- [ ] Tests: route-level pause/resume; UI-level approval handoff
  - Notes:
- [ ] Codereview + finalize
  - Notes:

## Working instructions (mandatory)

- Keep approval parameters minimal and validated via Zod schemas.
- Redact sensitive output from logs. Return concise tool results for LLM consumption.

## File & module targets

- `frontend/src/lib/tools/index.ts` (add sensitive tool)
- `frontend/src/app/api/chat/stream/route.ts` (wire tools + approval flow)
- `frontend/src/app/chat/page.tsx` (UI: approval prompt + response wiring)
- `frontend/tests/tools-approval/*.test.ts` (route + UI tests)

## Legacy mapping (delete later)

- Remove Python tool-calling wrappers and LangChain-specific glue related to approvals when parity is verified:
  - `tripsage_core/services/business/chat_service.py` tool dispatch sections
  - Any Python orchestration invoking approval flows

## Process flow (required)

1) Research: review Chatbot Tool Usage approval guidance
2) Plan: pick a single sensitive tool to validate flow end-to-end
3) Implement: server tool + approval flow; UI prompt and response
4) Test: simulate approval in unit/integration tests
5) Review: zen.codereview; fix; finalize

## Testing requirements

- Simulate tool request → pause → approval response → final message
- UI test: render approval prompt and submit approval; stream resumes and completes
