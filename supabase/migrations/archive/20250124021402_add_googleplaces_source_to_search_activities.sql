-- Migration: Add 'googleplaces' and 'ai_fallback' to search_activities.source CHECK constraint
-- Related: ADR-0053, SPEC-0030

ALTER TABLE public.search_activities
  DROP CONSTRAINT IF EXISTS search_activities_source_check,
  ADD CONSTRAINT search_activities_source_check
    CHECK (source IN ('viator','getyourguide','googleplaces','ai_fallback','external_api','cached'));

