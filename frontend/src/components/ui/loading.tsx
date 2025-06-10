/**
 * Comprehensive loading components index
 * Exports all loading-related components for easy importing
 */

// Base components
export { Skeleton, skeletonVariants } from "./skeleton";
export { LoadingSpinner, spinnerVariants } from "./loading-spinner";

// Loading states
export {
  LoadingOverlay,
  LoadingButton,
  LoadingContainer,
  PageLoading,
} from "./loading-states";

// Generic skeletons
export {
  AvatarSkeleton,
  CardSkeleton,
  ListItemSkeleton,
  TableSkeleton,
  FormSkeleton,
  ChartSkeleton,
} from "./loading-skeletons";

// Travel-specific skeletons
export {
  FlightSkeleton,
  HotelSkeleton,
  TripSkeleton,
  DestinationSkeleton,
  ItineraryItemSkeleton,
  ChatMessageSkeleton,
  SearchFilterSkeleton,
} from "./travel-skeletons";

// Hooks
export {
  useLoading,
  useAsyncLoading,
  useDebouncedLoading,
  type UseLoadingState,
  type UseLoadingOptions,
  type UseLoadingReturn,
  type UseAsyncLoadingReturn,
} from "../../hooks/use-loading";

// Types
export type {
  SkeletonConfig,
  LoadingSpinnerConfig,
  SkeletonProps,
  LoadingSpinnerBaseProps,
  LoadingOverlayProps,
  LoadingStateProps,
  LoadingContextValue,
} from "../../types/loading";

export { SkeletonType } from "../../types/loading";
