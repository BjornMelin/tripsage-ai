/**
 * @fileoverview Server page for hotel/accommodation search (RSC shell).
 */

import { submitHotelSearch } from "./actions";
import HotelsSearchClient from "./hotels-search-client";

export default function HotelSearchPage() {
  return <HotelsSearchClient onSubmitServer={submitHotelSearch} />;
}
