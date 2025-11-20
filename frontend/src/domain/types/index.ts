/**
 * @fileoverview Central export point for all domain types.
 *
 * This file re-exports all TypeScript types inferred from Zod schemas
 * in the @schemas directory.
 */

// Accommodations
export type {
  AccommodationBookingRequest,
  AccommodationBookingResult,
  AccommodationCheckAvailabilityParams,
  AccommodationCheckAvailabilityResult,
  AccommodationDetailsParams,
  AccommodationDetailsResult,
  AccommodationSearchParams,
  AccommodationSearchResult,
} from "../schemas/accommodations";
// agent-status.ts
export type {
  Agent,
  AgentActivity,
  AgentMetrics,
  AgentRuntimeConfig,
  AgentSession,
  AgentState,
  AgentStatusType,
  AgentTask,
  AgentWorkflow,
  CreateAgentRequest,
  CreateAgentTaskRequest,
  CreateWorkflowRequest,
  ResourceUsage,
  SessionStatus,
  TaskStatus,
  UpdateAgentRequest,
  UpdateAgentTaskRequest,
  UpdateWorkflowRequest,
  WorkflowConnection,
} from "../schemas/agent-status";
// api.ts
export type {
  ApiError,
  ApiKey,
  ApiResponse,
  AuthResponse,
  ChatMessage as ApiChatMessage,
  ChatMessage,
  ComputeRoutesRequest,
  ConfirmResetPasswordRequest,
  Conversation,
  CreateApiKeyRequest,
  CreateTripRequest,
  GeocodeRequest,
  LoginRequest,
  PaginatedResponse,
  PlacesDetailsRequest,
  PlacesPhotoRequest,
  PlacesSearchRequest,
  PostKeyBody,
  RefreshTokenRequest,
  RegisterRequest,
  ResetPasswordRequest,
  RouteMatrixRequest,
  SendMessageRequest,
  TimezoneRequest,
  Trip,
  UpdateApiKeyRequest,
  UpdateTripRequest,
  UpdateUserProfileRequest,
  UserProfile,
  WebSocketMessage,
  WebSocketSubscription,
} from "../schemas/api";
// auth.ts
export type {
  ChangePasswordFormData,
  ConfirmResetPasswordFormData,
  LoginFormData,
  RegisterFormData,
  ResetPasswordFormData,
} from "../schemas/auth";
// budget.ts
export type {
  Budget,
  BudgetCategory,
  BudgetSummary,
  Expense,
  ExpenseCategory,
} from "../schemas/budget";
// calendar.ts
export type {
  CalendarEvent,
  EventDateTime,
} from "../schemas/calendar";
// chat.ts
export type {
  Attachment,
  ChatCompletionRequest,
  ChatCompletionResponse,
  ChatSession,
  ConversationMessage,
  CreateConversationFormData,
  MemoryContextResponse,
  Message,
  MessagePart,
  MessageRole,
  SendMessageFormData,
  SendMessageOptions,
  TextPart,
  ToolCall,
  ToolCallState,
  ToolCallStatus,
  ToolResult,
} from "../schemas/chat";
// components.ts
export type {
  BudgetTrackerProps,
  ButtonProps,
  CardProps,
  ChatInterfaceProps,
  DashboardStatsProps,
  DialogProps,
  FormFieldProps,
  FormProps,
  InputProps,
  ItineraryBuilderProps,
  LoadingSpinnerProps,
  MessageItemProps,
  NavbarProps,
  QuickActionsProps,
  SearchFiltersProps,
  SearchFormProps,
  SearchResultsProps,
  SelectProps,
  SidebarProps,
  ToastProps,
  TripCardProps,
  TypingIndicatorProps,
} from "../schemas/components";
// configuration.ts
export type {
  AgentConfig as AppAgentConfig,
  AgentConfigRequest,
  AgentType,
  ConfigurationScope,
  ModelName,
  VersionId,
} from "../schemas/configuration";
// Expedia Rapid
export type {
  EpsCheckAvailabilityRequest,
  EpsCheckAvailabilityResponse,
  EpsCreateBookingRequest,
  EpsCreateBookingResponse,
  EpsPropertyDetailsRequest,
  EpsPropertyDetailsResponse,
  EpsSearchRequest,
  EpsSearchResponse,
  RapidAvailabilityResponse,
  RapidPriceCheckResponse,
  RapidPropertyContent,
  RapidRate,
} from "../schemas/expedia";

// contact.ts
// (No types exported from contact.ts yet, only schemas)

// errors.ts
export type {
  ErrorBoundaryProps,
  ErrorDetails,
  ErrorFallbackProps,
  ErrorInfo,
  ErrorReport,
  ErrorServiceConfig,
} from "../schemas/errors";

// loading.ts
export type {
  LoadingState,
  SkeletonProps,
} from "../schemas/loading";

// memory.ts
export type {
  Memory,
  SearchMemoriesFilters,
  SearchMemoriesRequest,
} from "../schemas/memory";

// profile.ts
export type {
  EmailUpdateFormData,
  PersonalInfoFormData,
  PreferencesFormData,
  SecuritySettingsFormData,
} from "../schemas/profile";

// providers.ts
export type {
  ModelMapper,
  ProviderId,
  ProviderResolution,
} from "../schemas/providers";

// realtime.ts
export type {
  AgentStatusBroadcastPayload,
  BackoffConfig,
  ChatMessageBroadcastPayload,
  ChatTypingBroadcastPayload,
  ConnectionStatus,
} from "../schemas/realtime";

// registry.ts
export type {
  Email,
  IsoDateTime,
  Timestamp,
  Url,
  Uuid,
} from "../schemas/registry";

// Search
export type {
  Accommodation,
  Activity,
  ActivitySearchParams,
  BaseSearchParams,
  Destination,
  DestinationSearchParams,
  FilterOption,
  FilterValue,
  Flight,
  FlightSearchParams,
  MetadataValue,
  SavedSearch,
  SearchAccommodationParams,
  SearchParams,
  SearchResponse,
  SearchResult,
  SearchResults,
  SearchType,
  SortOption,
} from "../schemas/search";

// Stores
export type {
  ApiKeyStoreActions,
  ApiKeyStoreState,
  AuthSession,
  AuthStoreActions,
  AuthStoreState,
  AuthTokenInfo,
  AuthUser,
  AuthUserPreferences,
  AuthUserSecurity,
  BudgetStoreActions,
  BudgetStoreState,
  ChatStoreActions,
  ChatStoreState,
  SearchStoreActions,
  SearchStoreState,
  TripStoreActions,
  TripStoreState,
  UiStoreActions,
  UiStoreState,
  UserStoreActions,
  UserStoreState,
} from "../schemas/stores";

// Supabase
export type {
  AccommodationSource,
  AccommodationsInsert,
  AccommodationsRow,
  AccommodationsUpdate,
  BookingStatus,
  FlightClass,
  FlightsInsert,
  FlightsRow,
  FlightsUpdate,
  Json,
  TripStatus,
  TripsInsert,
  TripsRow,
  TripsUpdate,
  TripType,
  UserSettingsInsert,
  UserSettingsRow,
  UserSettingsUpdate,
} from "../schemas/supabase";

// Temporal
export type {
  Availability,
  BusinessHours,
  DateRange,
  DateTimeRange,
  Duration,
  RecurrenceFrequency,
  RecurrenceRule,
  RecurringRule,
  TimeRange,
} from "../schemas/temporal";

// Theme Provider
export type { ValidatedThemeProviderProps } from "../schemas/theme-provider";

// Tokens
export type {
  ChatMessageRole,
  ClampResult,
  ModelLimitsTable,
  TokenChatMessage,
} from "../schemas/tokens";

// Trips
export type {
  ItineraryItemCreateInput,
  ItineraryItemUpdateInput,
  TripCreateInput,
  TripFilters,
  TripSuggestion,
  TripUpdateInput,
  TripVisibility,
} from "../schemas/trips";

// Validation
export type {
  ValidationContext,
  ValidationResult,
} from "../schemas/validation";

// Webhooks
export type {
  MemorySyncJob,
  NotifyJob,
  WebhookPayload,
} from "../schemas/webhooks";
