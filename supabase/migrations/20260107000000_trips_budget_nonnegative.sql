-- Trips: relax budget constraint to allow 0 (unknown budget)
-- Generated: 2026-01-07

ALTER TABLE public.trips
  DROP CONSTRAINT IF EXISTS trips_budget_check;

ALTER TABLE public.trips
  ADD CONSTRAINT trips_budget_check CHECK (budget >= 0);

ALTER TABLE public.trips
  ALTER COLUMN budget SET DEFAULT 0;

