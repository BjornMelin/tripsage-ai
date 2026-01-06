# SPEC-0105: Attachments (Supabase Storage + ingestion pipeline)

**Version**: 1.0.0  
**Status**: Final  
**Date**: 2026-01-05

## Goals

- Users can upload files into chat or trip context.
- Files are stored in Supabase Storage with strict access controls.
- Ingestion pipeline extracts text and indexes into RAG.

## Requirements

- Storage bucket: `attachments`
- Object key: `{userId}/{tripId?}/{chatId}/{attachmentId}/{filename}`
- Metadata table: `attachments` referencing storage path, mime, size, checksum.

## Pipeline

1) Upload request -> Server Action creates attachment record and returns signed upload URL.
2) Client uploads directly to Supabase Storage.
3) Supabase webhook or client callback triggers QStash job:
   - extract text (pdf, docx, txt)
   - chunk
   - embed and index into `rag_documents`

## Security

- No public buckets.
- RLS on metadata table.
- Signed URLs are short TTL.
- Antivirus scanning optional (documented).
