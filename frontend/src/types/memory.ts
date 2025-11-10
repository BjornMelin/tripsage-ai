/**
 * @fileoverview Memory-related types for frontend integration with the Mem0
 * backend.
 */

export interface Memory {
  id: string;
  content: string;
  type: string;
  userId: string;
  sessionId?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

export interface UserPreferences {
  destinations?: string[];
  activities?: string[];
  budgetRange?: {
    min: number;
    max: number;
    currency: string;
  };
  travelStyle?: string;
  accommodationType?: string[];
  transportationPreferences?: string[];
  dietaryRestrictions?: string[];
  accessibilityNeeds?: string[];
  languagePreferences?: string[];
  timePreferences?: {
    preferredDepartureTimes?: string[];
    tripDurationPreferences?: string[];
    seasonalityPreferences?: string[];
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
  metadata?: Record<string, unknown>;
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
    metadata?: Record<string, unknown>;
  };
  limit?: number;
  similarityThreshold?: number;
}

export interface SearchMemoriesResponse {
  success: boolean;
  memories: Array<{
    memory: Memory;
    similarityScore: number;
    relevanceReason: string;
  }>;
  totalFound: number;
  searchMetadata: {
    queryProcessed: string;
    searchTimeMs: number;
    similarityThresholdUsed: number;
  };
}

export interface UpdatePreferencesRequest {
  preferences: Partial<UserPreferences>;
  mergeStrategy?: "replace" | "merge" | "append";
}

export interface UpdatePreferencesResponse {
  success: boolean;
  updatedPreferences: UserPreferences;
  changesMade: string[];
  metadata: {
    updatedAt: string;
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
        percentageChange: number;
      }>;
    };
    destinationPreferences: {
      topDestinations: Array<{
        destination: string;
        visits: number;
        lastVisit: string;
        satisfactionScore?: number;
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
    analysisDate: string;
    dataCoverageMonths: number;
    confidenceLevel: number;
  };
}

export interface AddConversationMemoryRequest {
  messages: ConversationMessage[];
  userId: string;
  sessionId?: string;
  contextType?: string;
  metadata?: Record<string, unknown>;
}

export interface AddConversationMemoryResponse {
  success: boolean;
  memoriesCreated: string[];
  insightsGenerated: MemoryInsight[];
  updatedPreferences: Partial<UserPreferences>;
  metadata: {
    processingTimeMs: number;
    extractionMethod: string;
  };
}

export interface DeleteUserMemoriesResponse {
  success: boolean;
  deletedCount: number;
  backupCreated: boolean;
  backupLocation?: string;
  metadata: {
    deletionTime: string;
    userId: string;
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
