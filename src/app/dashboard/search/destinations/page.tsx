/**
 * @fileoverview Server page for destination search (RSC shell).
 */

import { submitDestinationSearch } from "./actions";
import DestinationsSearchClient from "./destinations-search-client";

/**
 * Destination search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The destination search page.
 */
export default function DestinationsSearchPage() {
  return <DestinationsSearchClient onSubmitServer={submitDestinationSearch} />;
}
