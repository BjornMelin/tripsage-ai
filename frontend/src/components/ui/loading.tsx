/**
 * @fileoverview Loading components index
 * Exports all loading-related components for easy importing
 */

// Hooks
export {
  type UseAsyncLoadingReturn,
  type UseLoadingOptions,
  type UseLoadingReturn,
  type UseLoadingState,
  useAsyncLoading,
  useDebouncedLoading,
  useLoading,
} from "../../hooks/use-loading";
// Generic skeletons
export {
  AvatarSkeleton,
  CardSkeleton,
  ChartSkeleton,
  FormSkeleton,
  ListItemSkeleton,
  TableSkeleton,
} from "./loading-skeletons";
export { LoadingSpinner, SpinnerVariants } from "./loading-spinner";
// Types re-exported from concrete component modules
export type { LoadingOverlayProps, LoadingStateProps } from "./loading-states";
// Loading states
export {
  LoadingButton,
  LoadingContainer,
  LoadingOverlay,
  PageLoading,
} from "./loading-states";
export type { SkeletonProps } from "./skeleton";
// Base components
export { Skeleton, SkeletonVariants } from "./skeleton";
// Travel-specific skeletons
export {
  ChatMessageSkeleton,
  DestinationSkeleton,
  FlightSkeleton,
  HotelSkeleton,
  ItineraryItemSkeleton,
  SearchFilterSkeleton,
  TripSkeleton,
} from "./travel-skeletons";
