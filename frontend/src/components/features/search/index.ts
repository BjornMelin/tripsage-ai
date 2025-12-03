/**
 * @fileoverview Search feature components exports.
 */

import type { FlightResult, HotelResult } from "@schemas/search";

// Results components
export { ActivityResults } from "./activity-results";
// Search forms
export { ActivitySearchForm } from "./activity-search-form";
export { DestinationSearchForm } from "./destination-search-form";
// Filter components
export { FilterPanel } from "./filter-panel";
export { FilterPresets } from "./filter-presets";
export { FlightResults } from "./flight-results";
export { FlightSearchForm } from "./flight-search-form";
export { HotelResults } from "./hotel-results";
export { HotelSearchForm } from "./hotel-search-form";

// Re-export types from schemas
export type { FlightResult, HotelResult };

// Other components
export { SearchAnalytics } from "./search-analytics";
export {
  AddToCollectionDropdown,
  SearchCollections,
} from "./search-collections";
