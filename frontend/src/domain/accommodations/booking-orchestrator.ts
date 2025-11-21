/**
 * @fileoverview Booking orchestrator sequencing approval -> payment -> provider booking -> persistence with compensation.
 *
 * Executes the full booking transaction with compensation: approvals, payment capture,
 * provider booking, Supabase persistence, and refund/alert handling on failure paths.
 */

import type {
  AccommodationProviderAdapter,
  ProviderResult,
} from "@domain/accommodations/providers/types";
import type { AccommodationBookingResult } from "@schemas/accommodations";
import type {
  EpsCreateBookingRequest,
  EpsCreateBookingResponse,
} from "@schemas/expedia";
import {
  type ProcessedPayment,
  refundBookingPayment,
} from "@/lib/payments/booking-payment";
import { secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/**
 * Command object for preparing a booking transaction.
 *
 * @param approvalKey - Key for approving the booking.
 * @param userId - User ID for the booking.
 * @param sessionId - Session ID for the booking.
 * @param idempotencyKey - Idempotency key for the booking.
 * @param bookingToken - Booking token for the booking.
 * @param amount - Amount for the booking.
 * @param currency - Currency for the booking.
 * @param paymentMethodId - Payment method ID for the booking.
 * @param guest - Guest details for the booking.
 * @param stay - Stay details for the booking.
 * @param providerPayload - Provider payload for the booking.
 * @param processPayment - Function to process the payment.
 * @param persistBooking - Function to persist the booking.
 * @param requestApproval - Function to request approval for the booking.
 */
export type BookingCommand = {
  approvalKey: string;
  userId: string;
  sessionId: string;
  idempotencyKey: string;
  bookingToken: string;
  amount: number;
  currency: string;
  paymentMethodId: string;
  guest: {
    name: string;
    email: string;
    phone?: string;
  };
  stay: {
    listingId: string;
    checkin: string;
    checkout: string;
    guests: number;
    specialRequests?: string;
    tripId?: string;
  };
  providerPayload: EpsCreateBookingRequest;
  processPayment: () => Promise<ProcessedPayment>;
  persistBooking: (payload: PersistPayload) => Promise<void>;
  requestApproval: () => Promise<void>;
};

/**
 * Payload for persisting a booking transaction.
 *
 * @param bookingId - ID of the booking.
 * @param epsItineraryId - ID of the itinerary.
 * @param stripePaymentIntentId - ID of the Stripe payment intent.
 * @param confirmationNumber - Confirmation number for the booking.
 * @param command - Booking command.
 */
type PersistPayload = {
  bookingId: string;
  epsItineraryId: string;
  stripePaymentIntentId: string;
  confirmationNumber: string;
  command: BookingCommand;
};

/**
 * Dependencies for the booking orchestrator.
 *
 * @param provider - Provider adapter.
 * @param supabase - Supabase client.
 */
export type BookingOrchestratorDeps = {
  provider: AccommodationProviderAdapter;
  supabase: TypedServerSupabase;
};

/**
 * Runs the booking workflow with telemetry and compensation safeguards.
 *
 * @param deps Provider adapter and Supabase client.
 * @param command Fully prepared booking command including approval/payment hooks.
 * @returns Confirmed booking result or propagates normalized provider/payment errors.
 */
export function runBookingOrchestrator(
  deps: BookingOrchestratorDeps,
  command: BookingCommand
): Promise<AccommodationBookingResult> {
  return withTelemetrySpan(
    "accommodations.book",
    {
      attributes: {
        listingId: command.stay.listingId,
        provider: deps.provider.name,
        userId: command.userId,
      },
      redactKeys: ["guest_email", "guest_phone"],
    },
    async (span) => {
      await command.requestApproval();

      const bookingId = secureUuid();
      let payment: ProcessedPayment | undefined;

      try {
        payment = await command.processPayment();
      } catch (error) {
        span.recordException(error as Error);
        throw error;
      }

      let providerResult: ProviderResult<EpsCreateBookingResponse>;
      try {
        providerResult = await deps.provider.createBooking(command.providerPayload, {
          sessionId: command.sessionId,
          userId: command.userId,
        });
      } catch (error) {
        await refundOnFailure(payment);
        span.recordException(error as Error);
        throw error;
      }

      if (!providerResult.ok) {
        await refundOnFailure(payment);
        throw providerResult.error;
      }

      const itineraryId =
        providerResult.value.itinerary_id ?? command.stay.tripId ?? bookingId;
      const confirmation =
        providerResult.value.rooms?.[0]?.confirmation_id?.expedia ??
        providerResult.value.rooms?.[0]?.confirmation_id?.property ??
        itineraryId;

      try {
        await command.persistBooking({
          bookingId,
          command,
          confirmationNumber: confirmation,
          epsItineraryId: itineraryId,
          stripePaymentIntentId: payment.paymentIntentId,
        });
      } catch (dbError) {
        emitOperationalAlert("booking.persistence_failed", {
          attributes: {
            bookingId,
            error: dbError instanceof Error ? dbError.message : "unknown",
            listingId: command.stay.listingId,
            userId: command.userId,
          },
          severity: "error",
        });
        span.recordException(dbError as Error);
        throw dbError;
      }

      const reference = confirmation ?? `bk_${bookingId.slice(0, 10)}`;

      return {
        bookingId,
        bookingStatus: "confirmed",
        checkin: command.stay.checkin,
        checkout: command.stay.checkout,
        epsBookingId: itineraryId,
        guestEmail: command.guest.email,
        guestName: command.guest.name,
        guestPhone: command.guest.phone,
        guests: command.stay.guests,
        holdOnly: false,
        idempotencyKey: command.idempotencyKey,
        listingId: command.stay.listingId,
        message: confirmation
          ? `Booking confirmed! Confirmation number: ${confirmation}`
          : "Booking confirmed, confirmation number pending persistence",
        paymentMethod: command.paymentMethodId,
        reference,
        specialRequests: command.stay.specialRequests,
        status: "success",
        stripePaymentIntentId: payment.paymentIntentId,
        tripId: command.stay.tripId,
      };
    }
  );
}

/**
 * Refund a booking payment if the payment intent ID is available.
 *
 * @param payment - The processed payment to refund.
 * @returns A promise that resolves when the refund is complete or rejected.
 */
async function refundOnFailure(payment?: ProcessedPayment): Promise<void> {
  if (!payment?.paymentIntentId) return;
  try {
    await refundBookingPayment(payment.paymentIntentId);
  } catch {
    emitOperationalAlert("booking.refund_failed", {
      attributes: {
        paymentIntentId: payment.paymentIntentId,
      },
      severity: "warning",
    });
  }
}
