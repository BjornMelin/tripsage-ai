-- Description: Add trip description field

ALTER TABLE public.trips
  ADD COLUMN IF NOT EXISTS description TEXT;
