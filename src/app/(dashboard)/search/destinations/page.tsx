/**
 * @fileoverview Server page for destination search (RSC shell).
 */

import { submitDestinationSearch } from "./actions";
import DestinationsSearchClient from "./destinations-search-client";

export const dynamic = "force-dynamic";

export default function DestinationsSearchPage() {
  return <DestinationsSearchClient onSubmitServer={submitDestinationSearch} />;
}
