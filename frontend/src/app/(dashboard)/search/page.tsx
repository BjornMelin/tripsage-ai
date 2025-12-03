/**
 * @fileoverview Server page for search hub (RSC shell).
 */

import SearchHubClient from "./search-hub-client";

export const dynamic = "force-dynamic";

export default function SearchPage() {
  return <SearchHubClient />;
}
