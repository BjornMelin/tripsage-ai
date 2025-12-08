# Storage Owner Audit Runbook

Operational checklist to detect and remediate ownership mismatches between Supabase Storage objects and relational records.

## Scope

- Buckets: `attachments`, `trip-images`, `avatars`.
- Tables: `storage.objects`, `public.file_attachments` (path + owner metadata).
- Purpose: ensure `owner`/`user_id` alignment for RLS and clean up orphaned objects.

## Prerequisites

- Supabase service-role key available for SQL execution.
- Migrations applied from `supabase/migrations/20251122000000_base_schema.sql` (RLS + owner_id/owner coalesce in storage policies).

## Detection Queries

**Objects without a matching file_attachments row**

```sql
SELECT o.bucket_id, o.name AS path, o.owner, o.created_at
FROM storage.objects o
LEFT JOIN public.file_attachments fa ON fa.file_path = o.name
WHERE o.bucket_id IN ('attachments','trip-images','avatars')
  AND fa.file_path IS NULL
ORDER BY o.created_at DESC;
```

**Owner mismatch between storage.objects and file_attachments**

```sql
SELECT o.bucket_id, o.name AS path, o.owner AS storage_owner, fa.user_id, fa.trip_id
FROM storage.objects o
JOIN public.file_attachments fa ON fa.file_path = o.name
WHERE o.bucket_id IN ('attachments','trip-images','avatars')
  AND (fa.user_id IS DISTINCT FROM o.owner OR fa.user_id IS NULL);
```

**file_attachments pointing to missing objects**

```sql
SELECT fa.id, fa.file_path, fa.user_id, fa.trip_id
FROM public.file_attachments fa
LEFT JOIN storage.objects o ON o.name = fa.file_path
WHERE o.name IS NULL
ORDER BY fa.created_at DESC;
```

## Remediation Steps

- For orphaned objects (query 1): decide whether to delete the object or recreate the relational row. Use `storage.objects` delete via service role if the file is not referenced.
- For owner mismatches (query 2): align `storage.objects.owner` to `fa.user_id` **or** correct `file_attachments.user_id` if the relational row is wrong. Keep `user_id` as the source of truth; update storage via service-role SQL:

```sql
UPDATE storage.objects o
SET owner = fa.user_id
FROM public.file_attachments fa
WHERE fa.file_path = o.name
  AND o.bucket_id IN ('attachments','trip-images','avatars')
  AND (fa.user_id IS DISTINCT FROM o.owner OR fa.user_id IS NULL);
```

- For missing objects (query 3): either remove the relational row or re-upload the file, depending on business need.

## Ongoing Hygiene

- Run queries weekly or before large refactors of attachments/upload flows.
- Add a lightweight CI smoke check (non-blocking) that ensures the SQL in queries (1) and (2) returns zero rows in staging.
- When changing RLS or path conventions, add a one-time audit using this runbook.

## Alerts (optional)

- Create a scheduled task (pg_cron or external job) that logs counts of each mismatch bucket to an ops dashboard; page only on spikes or non-zero counts for production.
