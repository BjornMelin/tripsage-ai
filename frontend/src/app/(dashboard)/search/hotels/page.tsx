/**
 * @fileoverview Server page for hotel/accommodation search (RSC shell).
 */

import { submitHotelSearch } from "./actions";
import HotelsSearchClient from "./hotels-search-client";

export const dynamic = "force-dynamic";

export default function HotelSearchPage() {
  return <HotelsSearchClient onSubmitServer={submitHotelSearch} />;
}
