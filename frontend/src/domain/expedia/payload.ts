/**
 * @fileoverview Payload builders for Expedia Rapid API requests.
 *
 * Functions to construct properly formatted request payloads for Expedia's
 * Rapid API, converting TripSage data structures to API-compatible formats.
 */

import type { EpsCreateBookingRequest } from "@/domain/schemas/expedia";

/**
 * Builds Rapid API itinerary creation payload from booking request.
 *
 * @param request - TripSage booking request data.
 * @returns Formatted payload for Rapid API itinerary creation.
 */
export function buildCreateItineraryPayload(request: EpsCreateBookingRequest) {
  const affiliateReference =
    request.affiliateReferenceId ?? request.bookingToken.slice(0, 28);
  const { givenName, familyName } = request.traveler;
  const billing = request.billingContact ?? {
    address: {
      city: "Unknown",
      countryCode: "US",
      line1: "Not Provided",
    },
    familyName,
    givenName,
  };

  return {
    // biome-ignore lint/style/useNamingConvention: API field name
    affiliate_reference_id: affiliateReference,
    email: request.contact.email,
    hold: request.hold ?? false,
    payments: [
      {
        // biome-ignore lint/style/useNamingConvention: API field name
        billing_contact: {
          address: {
            city: billing.address?.city ?? "Unknown",
            // biome-ignore lint/style/useNamingConvention: API field name
            country_code: billing.address?.countryCode ?? "US",
            // biome-ignore lint/style/useNamingConvention: API field name
            line_1: billing.address?.line1 ?? "Not Provided",
            // biome-ignore lint/style/useNamingConvention: API field name
            line_2: billing.address?.line2,
            // biome-ignore lint/style/useNamingConvention: API field name
            line_3: billing.address?.line3,
            // biome-ignore lint/style/useNamingConvention: API field name
            postal_code: billing.address?.postalCode,
            // biome-ignore lint/style/useNamingConvention: API field name
            state_province_code: billing.address?.stateProvinceCode,
          },
          // biome-ignore lint/style/useNamingConvention: API field name
          family_name: billing.familyName,
          // biome-ignore lint/style/useNamingConvention: API field name
          given_name: billing.givenName,
        },
        type: "affiliate_collect",
      },
    ],
    phone: {
      // biome-ignore lint/style/useNamingConvention: API field name
      area_code: request.contact.phoneAreaCode,
      // biome-ignore lint/style/useNamingConvention: API field name
      country_code: request.contact.phoneCountryCode ?? "1",
      number: request.contact.phoneNumber ?? "0000000",
    },
    rooms: [
      {
        // biome-ignore lint/style/useNamingConvention: API field name
        child_ages: request.stay.childAges,
        // biome-ignore lint/style/useNamingConvention: API field name
        family_name: familyName,
        // biome-ignore lint/style/useNamingConvention: API field name
        given_name: givenName,
        // biome-ignore lint/style/useNamingConvention: API field name
        number_of_adults: request.stay.adults,
        // biome-ignore lint/style/useNamingConvention: API field name
        special_request: request.specialRequests,
      },
    ],
    // biome-ignore lint/style/useNamingConvention: API field name
    special_requests: request.specialRequests,
    // biome-ignore lint/style/useNamingConvention: API field name
    traveler_handling_instructions: undefined,
  };
}
