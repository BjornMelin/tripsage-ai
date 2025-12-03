/**
 * @fileoverview Server page for activity search (RSC shell).
 */

import { type ActivitySearchParams, activitySearchParamsSchema } from "@schemas/search";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import ActivitiesSearchClient from "./activities-search-client";

export const dynamic = "force-dynamic";

export default function ActivitiesSearchPage() {
  return <ActivitiesSearchClient onSubmitServer={submitActivitySearch} />;
}

/**
 * Server action to validate and trace activity search submissions.
 *
 * @param params - Activity search parameters from the client.
 * @returns Validated activity search parameters.
 * @throws Error if validation fails.
 */
async function submitActivitySearch(params: ActivitySearchParams) {
  "use server";

  return await withTelemetrySpan(
    "search.activity.server.submit",
    { attributes: { destination: params.destination ?? "", searchType: "activity" } },
    () => {
      // Validate with Zod schema
      const validation = activitySearchParamsSchema.safeParse(params);
      if (!validation.success) {
        throw new Error(`Invalid activity search params: ${validation.error.message}`);
      }
      // Return validated params; client fetches results via hook
      return validation.data;
    }
  );
}
