/**
 * @fileoverview Server page for activity search (RSC shell).
 */

import { submitActivitySearch } from "./actions";
import ActivitiesSearchClient from "./activities-search-client";

/**
 * Activity search page that renders the client component and handles server submission.
 *
 * @returns {JSX.Element} The activity search page.
 */
export default function ActivitiesSearchPage() {
  return <ActivitiesSearchClient onSubmitServer={submitActivitySearch} />;
}
