-- Normalise bookings table for Amadeus/Stripe stack and remove EPS legacy fields.

DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'bookings'
      AND column_name = 'eps_booking_id'
  ) THEN
    ALTER TABLE public.bookings RENAME COLUMN eps_booking_id TO provider_booking_id;
  END IF;
END $$;

-- Ensure provider_booking_id is present and required.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'bookings'
      AND column_name = 'provider_booking_id'
  ) THEN
    ALTER TABLE public.bookings
      ADD COLUMN provider_booking_id TEXT;
  END IF;
END $$;

-- Make provider_booking_id mandatory for future writes.
ALTER TABLE public.bookings
  ALTER COLUMN provider_booking_id SET NOT NULL;

-- Refresh comments to remove EPS legacy references.
COMMENT ON TABLE public.bookings IS 'Stores accommodation booking confirmations for Amadeus + Google Places + Stripe stack';
COMMENT ON COLUMN public.bookings.id IS 'Internal booking identifier';
COMMENT ON COLUMN public.bookings.property_id IS 'Provider property identifier (Amadeus hotelId)';
COMMENT ON COLUMN public.bookings.provider_booking_id IS 'Provider confirmation / booking identifier';
COMMENT ON COLUMN public.bookings.booking_token IS 'Ephemeral booking token from availability step';
COMMENT ON COLUMN public.bookings.stripe_payment_intent_id IS 'Stripe PaymentIntent used for capture/refund';

