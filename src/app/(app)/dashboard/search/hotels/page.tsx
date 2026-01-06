/**
 * @fileoverview Server page for hotel/accommodation search (RSC shell).
 */

import { submitHotelSearch } from "./actions";
import HotelsSearchClient from "./hotels-search-client";

/**
 * Hotel search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The hotel search page.
 */
export default function HotelSearchPage() {
  return <HotelsSearchClient onSubmitServer={submitHotelSearch} />;
}
