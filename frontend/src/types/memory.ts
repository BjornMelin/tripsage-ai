// Memory-related types for frontend integration with Mem0 backend

export interface Memory {
  id: string;
  content: string;
  type: string;
  userId: string;
  sessionId?: string;
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

export interface UserPreferences {
  destinations?: string[];
  activities?: string[];
  budget_range?: {
    min: number;
    max: number;
    currency: string;
  };
  travel_style?: string;
  accommodation_type?: string[];
  transportation_preferences?: string[];
  dietary_restrictions?: string[];
  accessibility_needs?: string[];
  language_preferences?: string[];
  time_preferences?: {
    preferred_departure_times?: string[];
    trip_duration_preferences?: string[];
    seasonality_preferences?: string[];
  };
}

export interface MemoryInsight {
  category: string;
  insight: string;
  confidence: number;
  relatedMemories: string[];
  actionable: boolean;
}

export interface ConversationMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

// API Request/Response Types

export interface MemoryContextResponse {
  success: boolean;
  context: {
    userPreferences: UserPreferences;
    recentMemories: Memory[];
    insights: MemoryInsight[];
    travelPatterns: {
      frequentDestinations: string[];
      averageBudget: number;
      preferredTravelStyle: string;
      seasonalPatterns: Record<string, string[]>;
    };
  };
  metadata: {
    totalMemories: number;
    lastUpdated: string;
  };
}

export interface SearchMemoriesRequest {
  query: string;
  userId: string;
  filters?: {
    type?: string[];
    dateRange?: {
      start: string;
      end: string;
    };
    metadata?: Record<string, any>;
  };
  limit?: number;
  similarity_threshold?: number;
}

export interface SearchMemoriesResponse {
  success: boolean;
  memories: Array<{
    memory: Memory;
    similarity_score: number;
    relevance_reason: string;
  }>;
  total_found: number;
  search_metadata: {
    query_processed: string;
    search_time_ms: number;
    similarity_threshold_used: number;
  };
}

export interface UpdatePreferencesRequest {
  preferences: Partial<UserPreferences>;
  merge_strategy?: "replace" | "merge" | "append";
}

export interface UpdatePreferencesResponse {
  success: boolean;
  updated_preferences: UserPreferences;
  changes_made: string[];
  metadata: {
    updated_at: string;
    version: number;
  };
}

export interface MemoryInsightsResponse {
  success: boolean;
  insights: {
    travelPersonality: {
      type: string;
      confidence: number;
      description: string;
      keyTraits: string[];
    };
    budgetPatterns: {
      averageSpending: Record<string, number>;
      spendingTrends: Array<{
        category: string;
        trend: "increasing" | "decreasing" | "stable";
        percentage_change: number;
      }>;
    };
    destinationPreferences: {
      topDestinations: Array<{
        destination: string;
        visits: number;
        lastVisit: string;
        satisfaction_score?: number;
      }>;
      discoveryPatterns: string[];
    };
    recommendations: Array<{
      type: "destination" | "activity" | "budget" | "timing";
      recommendation: string;
      reasoning: string;
      confidence: number;
    }>;
  };
  metadata: {
    analysis_date: string;
    data_coverage_months: number;
    confidence_level: number;
  };
}

export interface AddConversationMemoryRequest {
  messages: ConversationMessage[];
  userId: string;
  sessionId?: string;
  context_type?: string;
  metadata?: Record<string, any>;
}

export interface AddConversationMemoryResponse {
  success: boolean;
  memories_created: string[];
  insights_generated: MemoryInsight[];
  updated_preferences: Partial<UserPreferences>;
  metadata: {
    processing_time_ms: number;
    extraction_method: string;
  };
}

export interface DeleteUserMemoriesResponse {
  success: boolean;
  deleted_count: number;
  backup_created: boolean;
  backup_location?: string;
  metadata: {
    deletion_time: string;
    user_id: string;
  };
}

// Component Props Types

export interface MemoryContextPanelProps {
  userId: string;
  sessionId?: string;
  className?: string;
  onMemorySelect?: (memory: Memory) => void;
}

export interface PersonalizationInsightsProps {
  userId: string;
  className?: string;
  showRecommendations?: boolean;
  onPreferenceUpdate?: (preferences: Partial<UserPreferences>) => void;
}

export interface MemorySearchProps {
  userId: string;
  onResultSelect?: (memory: Memory) => void;
  placeholder?: string;
  className?: string;
  maxResults?: number;
}

// Store Types

export interface MemoryState {
  currentUserContext: MemoryContextResponse | null;
  searchResults: SearchMemoriesResponse | null;
  insights: MemoryInsightsResponse | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchUserContext: (userId: string) => Promise<void>;
  searchMemories: (request: SearchMemoriesRequest) => Promise<void>;
  updatePreferences: (
    userId: string,
    preferences: Partial<UserPreferences>
  ) => Promise<void>;
  addConversationMemory: (request: AddConversationMemoryRequest) => Promise<void>;
  clearMemories: (userId: string) => Promise<void>;
  clearError: () => void;
}
