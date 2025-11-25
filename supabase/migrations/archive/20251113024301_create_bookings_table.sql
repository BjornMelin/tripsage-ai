-- Create bookings table for accommodation reservations
-- Stores booking confirmations from Expedia Partner Solutions (EPS)

CREATE TABLE IF NOT EXISTS public.bookings (
  id TEXT PRIMARY KEY, -- EPS booking confirmation ID
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  property_id TEXT NOT NULL, -- EPS property ID (e.g., 'eps:12345')
  status TEXT NOT NULL CHECK (status IN ('CONFIRMED', 'PENDING', 'CANCELLED', 'REFUNDED')),
  booking_token TEXT, -- EPS booking token (temporary, expires)
  stripe_payment_intent_id TEXT, -- Stripe payment intent ID for refunds
  eps_booking_id TEXT, -- Final EPS booking confirmation ID
  
  -- Booking dates
  checkin DATE NOT NULL,
  checkout DATE NOT NULL,
  
  -- Guest information
  guest_email TEXT NOT NULL,
  guest_name TEXT NOT NULL,
  guest_phone TEXT,
  
  -- Booking metadata
  guests INT NOT NULL CHECK (guests > 0 AND guests <= 16),
  special_requests TEXT,
  trip_id UUID REFERENCES public.trips(id) ON DELETE SET NULL,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS bookings_user_id_idx ON public.bookings(user_id);
CREATE INDEX IF NOT EXISTS bookings_status_idx ON public.bookings(status);
CREATE INDEX IF NOT EXISTS bookings_checkin_idx ON public.bookings(checkin);
CREATE INDEX IF NOT EXISTS bookings_property_id_idx ON public.bookings(property_id);
CREATE INDEX IF NOT EXISTS bookings_trip_id_idx ON public.bookings(trip_id);
CREATE INDEX IF NOT EXISTS bookings_created_at_idx ON public.bookings(created_at DESC);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_bookings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
CREATE TRIGGER update_bookings_updated_at
  BEFORE UPDATE ON public.bookings
  FOR EACH ROW
  EXECUTE FUNCTION update_bookings_updated_at();

-- Add RLS policies
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only see their own bookings
CREATE POLICY "Users can view their own bookings"
  ON public.bookings
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Policy: Users can create their own bookings
CREATE POLICY "Users can create their own bookings"
  ON public.bookings
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Policy: Users can update their own bookings (for status changes)
CREATE POLICY "Users can update their own bookings"
  ON public.bookings
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Policy: Service role can manage all bookings (for webhooks, admin)
CREATE POLICY "Service role can manage all bookings"
  ON public.bookings
  FOR ALL
  TO service_role
  USING (true)
  WITH CHECK (true);

-- Add comments
COMMENT ON TABLE public.bookings IS 'Stores accommodation booking confirmations from Expedia Partner Solutions';
COMMENT ON COLUMN public.bookings.booking_token IS 'Temporary EPS booking token (expires after short period)';
COMMENT ON COLUMN public.bookings.stripe_payment_intent_id IS 'Stripe payment intent ID for refund processing';

