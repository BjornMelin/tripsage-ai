/**
 * @fileoverview Booking orchestrator with compensation.
 *
 * Executes booking workflow: approval -> payment -> provider booking -> persistence.
 * Handles refunds and alerts on failure paths.
 */

import type {
  AccommodationProviderAdapter,
  ProviderResult,
} from "@domain/accommodations/providers/types";
import type { AccommodationBookingResult } from "@schemas/accommodations";
import {
  type ProcessedPayment,
  refundBookingPayment,
} from "@/lib/payments/booking-payment";
import { secureUuid } from "@/lib/security/random";
import type { TypedServerSupabase } from "@/lib/supabase/server";
import { emitOperationalAlert } from "@/lib/telemetry/alerts";
import { withTelemetrySpan } from "@/lib/telemetry/span";

/** Command object for booking transaction execution. */
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
  providerPayload: ProviderPayloadBuilder;
  processPayment: () => Promise<ProcessedPayment>;
  persistBooking: (payload: PersistPayload) => Promise<void>;
  requestApproval: () => Promise<void>;
};

/** Provider payload builder function or static object. */
type ProviderPayloadBuilder =
  | Record<string, unknown>
  | ((payment: ProcessedPayment) => Record<string, unknown>);

/** Payload for persisting booking transaction to database. */
type PersistPayload = {
  bookingId: string;
  providerBookingId?: string;
  stripePaymentIntentId: string;
  confirmationNumber: string;
  command: BookingCommand;
};

/** Dependencies for booking orchestrator. */
export type BookingOrchestratorDeps = {
  provider: AccommodationProviderAdapter;
  supabase: TypedServerSupabase;
};

/**
 * Executes booking workflow with telemetry and compensation.
 *
 * @param deps - Provider adapter and Supabase client.
 * @param command - Booking command with approval and payment hooks.
 * @returns Confirmed booking result or throws provider/payment error.
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

      let providerResult: ProviderResult<{
        itineraryId?: string;
        confirmationNumber?: string;
        providerBookingId?: string;
      }>;
      let providerPayload: Record<string, unknown>;
      if (typeof command.providerPayload === "function") {
        if (!payment) {
          throw new Error("payment_missing");
        }
        providerPayload = command.providerPayload(payment);
      } else {
        providerPayload = command.providerPayload;
      }

      try {
        providerResult = await deps.provider.createBooking(providerPayload, {
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
        providerResult.value.itineraryId ?? command.stay.tripId ?? bookingId;
      const confirmation = providerResult.value.confirmationNumber ?? itineraryId;

      try {
        await command.persistBooking({
          bookingId,
          command,
          confirmationNumber: confirmation,
          providerBookingId: providerResult.value.providerBookingId ?? itineraryId,
          stripePaymentIntentId: payment.paymentIntentId,
        });
      } catch (dbError) {
        await refundOnFailure(payment);
        emitOperationalAlert("booking.persistence_failed", {
          attributes: {
            bookingId,
            error: dbError instanceof Error ? dbError.message : "unknown",
            listingId: command.stay.listingId,
            refundAttempted: Boolean(payment?.paymentIntentId),
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
        providerBookingId: itineraryId,
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
 * Refunds booking payment if payment intent ID is available.
 *
 * @param payment - Processed payment to refund.
 */
async function refundOnFailure(payment?: ProcessedPayment): Promise<void> {
  if (!payment?.paymentIntentId) return;
  try {
    await refundBookingPayment(payment.paymentIntentId);
  } catch (refundError) {
    emitOperationalAlert("booking.refund_failed", {
      attributes: {
        paymentIntentId: payment.paymentIntentId,
        refundError:
          refundError instanceof Error ? refundError.message : "unknown_refund_error",
      },
      severity: "warning",
    });
  }
}
