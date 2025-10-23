# Spec: Supabase SSR + Strict Typing Cleanup

Owner: Frontend Platform
Status: In progress
Last updated: 2025-10-23

## Objective

Finalize migration to `@supabase/ssr` and restore strict typing by removing temporary `(supabase as any)` casts in inserts/updates/selects.

## Implementation Checklist

- [x] Browser client: `src/lib/supabase/client.ts` uses `createBrowserClient<Database>`.
- [ ] Server client: add `src/lib/supabase/server.ts`:
  - [ ] `export function createServerClient()` using `@supabase/ssr` with cookie adapters from `next/headers`.
- [ ] Replace any-casts with typed calls:
  - [ ] `src/hooks/use-supabase-chat.ts` — parameterize `.insert<InsertTables<'chat_sessions'>>([{...}])` and `.update<UpdateTables<'chat_sessions'>>({...})` etc.
  - [ ] `src/hooks/use-supabase-storage.ts` — type `file_attachments` queries with `InsertTables/UpdateTables`.
  - [ ] `src/hooks/use-trips-supabase.ts` — type `trips` insert/update.
  - [ ] `src/stores/trip-store.ts` — type create/update trip paths.
- [x] Reinstate convenience exports in `database.types.ts` for app imports (ChatRole, FileAttachmentInsert/Update, ChatToolCallInsert, etc.).
- [ ] Add unit tests for typed insert/update builders (narrow smoke tests only).

## Notes

- PostgREST generics are strict; use array form for `insert([{ ... }])` and ensure the generic matches the table insert shape.
