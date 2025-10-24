# Spec: Supabase SSR + Strict Typing Cleanup

Owner: Frontend Platform
Status: In progress
Last updated: 2025-10-23

## Objective

Finalize migration to `@supabase/ssr` and restore strict typing by removing temporary `(supabase as any)` casts in inserts/updates/selects.

## Implementation Checklist

- [x] Browser client: `src/lib/supabase/client.ts` uses `createBrowserClient<Database>`.
- [x] Server client: `src/lib/supabase/server.ts` exists
  - [x] `export async function createServerSupabase()` using `@supabase/ssr` + `next/headers` cookie bridge.
- [x] Replace any-casts in hooks via centralized typed helpers:
  - [x] `src/hooks/use-supabase-chat.ts` — uses `insertSingle`/`updateSingle` wrappers enforcing `InsertTables/UpdateTables` at compile-time; ChatRole/ToolCallStatus aligned to DB enums. Stats query typed.
  - [x] `src/hooks/use-supabase-storage.ts` — typed stats shape; `file_attachments` insert/update via helpers; delete path casts selected row to `FileAttachment` prior to storage ops.
  - [x] `src/hooks/use-trips-supabase.ts` — `trips` insert/update via helpers; null-safe guard when RLS omits row.
  - [ ] `src/stores/trip-store.ts` — pending. Store schema diverges from DB; route through API or add repository layer before enforcing types.
- [x] Reinstate convenience exports in `database.types.ts` for app imports (ChatRole, FileAttachmentInsert/Update, ChatToolCallInsert, etc.).
- [ ] Add unit tests for typed insert/update builders (narrow smoke tests only).

## Notes

- We centralized PostgREST calls behind `src/lib/supabase/typed-helpers.ts` to avoid scattering `any` casts and ensure compile-time shape checks. The helpers currently return `{ data, error }`; extend if PostgREST response metadata is needed.
- PostgREST generics are strict; for direct usage prefer array form for `insert([{ ... }])` if needed.
- Trip store requires a mapping strategy (UI model ↔ DB schema). See ADR-0018.
