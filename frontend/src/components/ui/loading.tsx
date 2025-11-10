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
// Types
export type {
  LoadingContextValue,
  LoadingOverlayProps,
  LoadingSpinnerBaseProps,
  LoadingSpinnerConfig,
  LoadingStateProps,
  SkeletonConfig,
  SkeletonProps,
} from "../../types/loading";
export { SkeletonType } from "../../types/loading";

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
// Loading states
export {
  LoadingButton,
  LoadingContainer,
  LoadingOverlay,
  PageLoading,
} from "./loading-states";
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
