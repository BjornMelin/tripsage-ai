# Task Index (v1.0.0)

This is the master task list. Each P0/P1 should have its own task file in `docs/tasks/`.

Columns: `ID | Priority | Status | Owner | Summary | Dependencies`

## P0

T-001 | P0 | DONE | release-orchestrator | Dev server env validation blocks `pnpm dev` | -
T-002 | P0 | DONE | codex-session-t002-a | Fix Chromium e2e failures (dashboard load + theme toggle banner) | T-001
T-006 | P0 | DONE | release-orchestrator | Fix marketing navbar “Sign up” link (/signup 404) | -
T-007 | P0 | DONE | release-orchestrator | Add `/privacy`, `/terms`, `/contact` pages (fix broken legal links) | -
T-010 | P0 | DONE | codex-session-t010-a | UI audit: fix auth page layout + remove duplicate navbar | -

## P1

T-003 | P1 | DONE | codex-session-t003-a | Make `pnpm test:e2e` runnable (browser installs/docs/config) | -
T-004 | P1 | UNCLAIMED | - | Deployment readiness (Vercel deploy strategy + env inventory) | -
T-005 | P1 | DONE | codex-session-rag-finalization | Supabase RLS + Storage policy audit (least privilege) | -
T-008 | P1 | DONE | codex-session-t008-gpt52 | Implement “Plan New Trip” create flow (fix /dashboard/trips/create) | T-002
T-009 | P1 | DONE | release-orchestrator | Fix `/reset-password` “Contact support” link (/support 404) | -

## P2

`TBD`
