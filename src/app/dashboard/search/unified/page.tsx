/**
 * @fileoverview Server page for unified search experience (RSC shell).
 */

import { searchHotelsAction } from "./actions";
import UnifiedSearchClient from "./unified-search-client";

/** Server page for unified search experience (RSC shell). */
export default function UnifiedSearchPage() {
  return <UnifiedSearchClient onSearchHotels={searchHotelsAction} />;
}
