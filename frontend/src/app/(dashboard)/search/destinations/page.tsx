/**
 * @fileoverview Server page for destination search (RSC shell).
 */

import type { DestinationSearchParams } from "@schemas/search";
import { withTelemetrySpan } from "@/lib/telemetry/span";
import DestinationsSearchClient from "./destinations-search-client";

export const dynamic = "force-dynamic";

export default function DestinationsSearchPage() {
  return <DestinationsSearchClient onSubmitServer={submitDestinationSearch} />;
}

async function submitDestinationSearch(params: DestinationSearchParams) {
  "use server";

  return await withTelemetrySpan(
    "search.destination.server.submit",
    { attributes: { searchType: "destination" } },
    () => {
      // Only trace server-side receipt; client still fetches results.
      return params;
    }
  );
}
