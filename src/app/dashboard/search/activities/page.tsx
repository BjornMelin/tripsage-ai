/**
 * @fileoverview Server page for activity search (RSC shell).
 */

import dynamic from "next/dynamic";
import { SearchPageSkeleton } from "@/components/search/search-page-skeleton";
import { submitActivitySearch } from "./actions";

const ACTIVITIES_SEARCH_CLIENT = dynamic(() => import("./activities-search-client"), {
  loading: () => <SearchPageSkeleton />,
});

/**
 * Activity search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The activity search page.
 */
export default function ActivitiesSearchPage() {
  return <ACTIVITIES_SEARCH_CLIENT onSubmitServer={submitActivitySearch} />;
}
