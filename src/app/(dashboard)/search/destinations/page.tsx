/**
 * @fileoverview Server page for destination search (RSC shell).
 */

import { submitDestinationSearch } from "./actions";
import DestinationsSearchClient from "./destinations-search-client";

export default function DestinationsSearchPage() {
  return <DestinationsSearchClient onSubmitServer={submitDestinationSearch} />;
}
