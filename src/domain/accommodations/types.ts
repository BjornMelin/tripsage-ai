/**
 * @fileoverview Domain types shared with accommodations persistence adapters.
 */

export type AccommodationBookingInsert = {
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  booking_token: string;
  checkin: string;
  checkout: string;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  guest_email: string;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  guest_name: string;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  guest_phone: string | null;
  guests: number;
  id: string;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  property_id: string;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  provider_booking_id: string;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  special_requests: string | null;
  status: "CONFIRMED";
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  stripe_payment_intent_id: string | null;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  trip_id: number | null;
  // biome-ignore lint/style/useNamingConvention: database columns use snake_case
  user_id: string;
};

export type TripOwnership = {
  id: number;
  userId: string;
};
