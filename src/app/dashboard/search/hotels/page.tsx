/**
 * @fileoverview Server page for hotel/accommodation search (RSC shell).
 */

import dynamic from "next/dynamic";
import { SearchPageSkeleton } from "@/components/search/search-page-skeleton";
import { submitHotelSearch } from "./actions";

const HOTELS_SEARCH_CLIENT = dynamic(() => import("./hotels-search-client"), {
  loading: () => <SearchPageSkeleton />,
});

/**
 * Hotel search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The hotel search page.
 */
export default function HotelSearchPage() {
  return <HOTELS_SEARCH_CLIENT onSubmitServer={submitHotelSearch} />;
}
