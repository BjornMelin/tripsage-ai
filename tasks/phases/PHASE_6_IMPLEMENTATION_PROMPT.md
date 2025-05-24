# Phase 6: Frontend-Backend Integration & User Experience Enhancement - Implementation Prompt

## Context
✅ **Phase 5 Complete** - Phase 5 (Database Integration & Chat Agent Enhancement) was successfully completed with MCP-based database operations, chat agent orchestration, and comprehensive tool calling integration. Phase 1 (Chat API Enhancement), Phase 2 (Authentication & BYOK), Phase 3 (Testing Infrastructure), and Phase 4 (File Handling & Attachments) were all completed successfully.

## Your Task
Implement Phase 6: Frontend-Backend Integration & User Experience Enhancement as outlined in the analysis of `TODO.md`, `tasks/TODO-FRONTEND.md`, and project documentation. This phase connects the React frontend to the functional backend systems, creating a seamless end-to-end user experience for AI-powered travel planning.

## Tool Usage Instructions

### 1. Pre-Implementation Research Protocol
Use MCP tools to thoroughly research before coding:

```bash
# 1. Frontend Integration & UX Research
context7__resolve-library-id --libraryName "Next.js API integration patterns"
context7__get-library-docs --context7CompatibleLibraryID [resolved-id] --topic "authentication"
firecrawl__firecrawl_scrape --url "https://nextjs.org/docs/app/building-your-application/authentication" --formats ["markdown"]

# 2. Real-time Communication Patterns
exa__web_search_exa --query "WebSocket integration Next.js FastAPI real-time chat 2024" --numResults 5
tavily__tavily-search --query "Server-Sent Events SSE React streaming responses" --max_results 5

# 3. State Management & API Integration
firecrawl__firecrawl_deep_research --query "Zustand state management React API integration best practices"
perplexity__perplexity_research --messages [{"role": "user", "content": "How to implement robust error handling and loading states in React applications with backend APIs?"}]
```

### 2. Codebase Examination
```bash
# Read existing patterns first
- Read tool: tasks/TODO-FRONTEND.md (all sections)
- Read tool: frontend/src/components/features/ (all components)
- Read tool: frontend/src/lib/hooks/ (existing hooks)
- Read tool: frontend/src/stores/ (Zustand stores)
- Read tool: tripsage/api/routers/ (backend API endpoints)
- Read tool: frontend/src/app/api/ (Next.js API routes)
- Glob tool: frontend/src/**/*auth*.{ts,tsx} to understand auth patterns
- Glob tool: frontend/src/**/*chat*.{ts,tsx} to understand chat components
```

### 3. Task Management
```bash
# Create comprehensive TODO list
TodoWrite tool to create task list based on Phase 6 requirements + research findings

# Check current tasks
TodoRead tool to review progress and remaining items

# Update task status during implementation
TodoWrite tool to mark tasks as in_progress and completed
```

### 4. Git Workflow Protocol
```bash
# 1. Create feature branch
git checkout -b feature/frontend-backend-integration-phase6
git push -u origin feature/frontend-backend-integration-phase6

# 2. Commit with conventional format during development
git add .
git commit -m "feat: integrate authentication system with backend APIs"
git commit -m "feat: implement real-time chat with WebSocket connection"
git commit -m "feat: connect search components to live MCP backend"
git commit -m "feat: add trip management with database persistence"
git commit -m "test: add comprehensive E2E user flow tests"

# 3. Create PR when ready
gh pr create --title "feat: implement Phase 6 frontend-backend integration" --body "
## Summary
- Connects React frontend to functional backend systems
- Implements real-time chat with AI agents and tool calling
- Adds complete trip planning workflow with data persistence
- Creates seamless user experience for travel planning

## Changes
- Authentication integration with JWT and protected routes
- Real-time chat interface with streaming responses
- Trip management with live data from MCP services
- User dashboard with API key management and preferences
- Comprehensive error handling and loading states

## Testing
- All unit tests pass (≥90% coverage)
- E2E tests verify complete user workflows
- Integration tests validate API connections
- Performance tests ensure responsive user experience

🤖 Generated with Claude Code
"
```

### 5. Implementation Order
1. Authentication Integration & User Management (Section 6.1)
2. Real-time Chat Integration (Section 6.2) 
3. Trip Planning & Data Persistence (Section 6.3)
4. Search Components & Live Data (Section 6.4)
5. User Experience Enhancements (Section 6.5)
6. Testing & Performance Optimization (Section 6.6)

### 6. Key Files to Modify/Create
```
Frontend:
- frontend/src/lib/api/auth-client.ts (new - authentication client)
- frontend/src/hooks/use-websocket.ts (new - WebSocket hook)
- frontend/src/components/features/chat/real-time-chat.tsx (enhance - live backend)
- frontend/src/stores/auth-store.ts (enhance - JWT management)
- frontend/src/app/(dashboard)/trips/[id]/page.tsx (enhance - live data)
- frontend/src/components/features/search/*.tsx (enhance - API integration)

Backend:
- tripsage/api/routers/websocket.py (new - WebSocket endpoints)
- tripsage/api/middlewares/cors.py (enhance - frontend CORS)
- tripsage/services/user_session.py (new - session management)

Testing:
- frontend/e2e/user-flow.spec.ts (new - complete E2E tests)
- frontend/src/__tests__/integration/api-integration.test.ts (new)
```

### 7. Enhanced Testing Standards
**TARGET: ≥90% Test Coverage (frontend) + Comprehensive E2E Coverage**

```bash
# Frontend Testing
- Unit tests: frontend/src/__tests__/components/
- Hook tests: frontend/src/__tests__/hooks/
- Integration tests: frontend/src/__tests__/integration/
- E2E tests: frontend/e2e/

# Test Execution
cd frontend && pnpm test --coverage
cd frontend && pnpm e2e
cd /home/bjorn/repos/agents/openai/tripsage-ai && uv run pytest --cov=tripsage --cov-report=term-missing
```

**Critical Test Cases:**
- ✅ Complete user registration and authentication flow
- ✅ Real-time chat with AI agents and tool calling
- ✅ Trip planning workflow with live data persistence
- ✅ Search functionality with MCP backend integration
- ✅ API key management and BYOK functionality
- ✅ Error handling and offline mode graceful degradation
- ✅ Mobile responsiveness and touch interactions
- ✅ Performance under concurrent user sessions

### 8. KISS Principle Enforcement
**"Always do the simplest thing that works" - Question all complexity**

```bash
# Implementation Checkpoints
□ Can we use existing UI components instead of new ones?
□ Are we implementing only explicitly needed features? (YAGNI)
□ Is the API integration using standard fetch patterns?
□ Are we avoiding over-engineering the state management?
□ Have we documented WHY certain integration patterns were chosen?

# Complexity Challenges
- Authentication: Use standard JWT patterns, avoid complex session management
- Real-time Updates: Start with polling, upgrade to WebSocket only when needed
- State Management: Use existing Zustand stores, avoid unnecessary complexity
- Error Handling: Use established error boundary patterns
- Performance: Optimize incrementally based on actual bottlenecks
```

**Decision Documentation:** For any non-obvious choice, document the reasoning:
```typescript
// Choice: Using Server-Sent Events for chat streaming instead of WebSocket
// Reason: KISS principle - simpler implementation for one-way streaming
// Future: Can upgrade to WebSocket when bidirectional communication needed
```

## Phase 6 Checklist

### 6.1 Authentication Integration & User Management
- [ ] Integrate frontend auth components with FastAPI backend
- [ ] Implement JWT token management and refresh logic
- [ ] Add protected route middleware for authenticated pages
- [ ] Connect user profile components to user service APIs
- [ ] Implement BYOK API key management interface
- [ ] Add password reset and email verification flows
- [ ] Create user preferences and settings management
- [ ] Implement secure logout with token cleanup

### 6.2 Real-time Chat Integration
- [ ] Connect chat interface to backend chat agent controller
- [ ] Implement WebSocket/SSE for real-time message streaming
- [ ] Add typing indicators and agent status updates
- [ ] Handle tool calling responses in chat UI
- [ ] Implement conversation history persistence
- [ ] Add message retry and error handling
- [ ] Create chat session management
- [ ] Add file attachment integration with chat

### 6.3 Trip Planning & Data Persistence  
- [ ] Connect trip planning components to trip service APIs
- [ ] Implement trip saving, editing, and deletion
- [ ] Add real-time trip updates from AI planning sessions
- [ ] Create trip sharing and collaboration features
- [ ] Implement budget tracking with live data
- [ ] Add itinerary building with MCP data sources
- [ ] Create trip comparison and analytics
- [ ] Implement trip export functionality

### 6.4 Search Components & Live Data
- [ ] Connect flight search to Duffel MCP backend
- [ ] Integrate accommodation search with Airbnb MCP
- [ ] Add destination research with Maps and Web Crawl MCPs
- [ ] Implement activity search with live data sources
- [ ] Add search result caching and pagination
- [ ] Create search filters with backend validation
- [ ] Implement search history and favorites
- [ ] Add price tracking and alerts

### 6.5 User Experience Enhancements
- [ ] Implement responsive design for mobile devices
- [ ] Add loading states and skeleton screens
- [ ] Create error boundaries with retry mechanisms
- [ ] Implement offline mode with cached data
- [ ] Add accessibility features (ARIA, keyboard navigation)
- [ ] Create onboarding flow for new users
- [ ] Implement notifications and alerts system
- [ ] Add dark mode and theme customization

### 6.6 Testing & Performance Optimization
- [ ] Create comprehensive E2E user flow tests
- [ ] Add integration tests for API connections
- [ ] Implement performance tests for loading times
- [ ] Add accessibility testing with axe-core
- [ ] Create visual regression tests
- [ ] Implement bundle size optimization
- [ ] Add error tracking and monitoring
- [ ] Create user analytics and feedback collection

## Code Patterns to Follow

### Authentication Integration
```typescript
// In frontend/src/lib/api/auth-client.ts
import { toast } from 'sonner';

interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

class AuthClient {
  private baseUrl = process.env.NEXT_PUBLIC_API_URL;
  private token: string | null = null;

  async login(email: string, password: string): Promise<AuthResponse> {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    if (!response.ok) {
      const error = await response.json();
      toast.error(error.detail || 'Login failed');
      throw new Error(error.detail);
    }

    const data = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async authenticatedFetch(url: string, options: RequestInit = {}) {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${this.token}`,
      'Content-Type': 'application/json',
    };

    const response = await fetch(url, { ...options, headers });
    
    if (response.status === 401) {
      await this.refreshToken();
      // Retry with new token
      return this.authenticatedFetch(url, options);
    }

    return response;
  }

  private setToken(token: string) {
    this.token = token;
    localStorage.setItem('auth_token', token);
  }
}

export const authClient = new AuthClient();
```

### Real-time Chat Integration
```typescript
// In frontend/src/hooks/use-websocket.ts
import { useRef, useEffect, useCallback } from 'react';
import { useAuthStore } from '@/stores/auth-store';

interface UseWebSocketOptions {
  onMessage: (data: any) => void;
  onError?: (error: Event) => void;
  onConnect?: () => void;
}

export function useWebSocket(options: UseWebSocketOptions) {
  const { token } = useAuthStore();
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!token) return;

    const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws?token=${token}`;
    ws.current = new WebSocket(wsUrl);

    ws.current.onopen = () => {
      reconnectAttempts.current = 0;
      options.onConnect?.();
    };

    ws.current.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        options.onMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.current.onerror = (error) => {
      options.onError?.(error);
    };

    ws.current.onclose = () => {
      if (reconnectAttempts.current < maxReconnectAttempts) {
        setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, Math.pow(2, reconnectAttempts.current) * 1000);
      }
    };
  }, [token, options]);

  const sendMessage = useCallback((message: any) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    }
  }, []);

  const disconnect = useCallback(() => {
    ws.current?.close();
    ws.current = null;
  }, []);

  useEffect(() => {
    connect();
    return disconnect;
  }, [connect, disconnect]);

  return { sendMessage, disconnect, isConnected: ws.current?.readyState === WebSocket.OPEN };
}
```

### Trip Management Integration
```typescript
// In frontend/src/lib/api/trips-client.ts
import { authClient } from './auth-client';

interface Trip {
  id: string;
  title: string;
  destination: string;
  start_date: string;
  end_date: string;
  budget: number;
  status: 'planning' | 'booked' | 'completed';
}

class TripsClient {
  private baseUrl = process.env.NEXT_PUBLIC_API_URL;

  async getTrips(): Promise<Trip[]> {
    const response = await authClient.authenticatedFetch(`${this.baseUrl}/trips`);
    
    if (!response.ok) {
      throw new Error('Failed to fetch trips');
    }

    return response.json();
  }

  async createTrip(tripData: Partial<Trip>): Promise<Trip> {
    const response = await authClient.authenticatedFetch(`${this.baseUrl}/trips`, {
      method: 'POST',
      body: JSON.stringify(tripData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to create trip');
    }

    return response.json();
  }

  async updateTrip(id: string, updates: Partial<Trip>): Promise<Trip> {
    const response = await authClient.authenticatedFetch(`${this.baseUrl}/trips/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });

    if (!response.ok) {
      throw new Error('Failed to update trip');
    }

    return response.json();
  }

  async deleteTrip(id: string): Promise<void> {
    const response = await authClient.authenticatedFetch(`${this.baseUrl}/trips/${id}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      throw new Error('Failed to delete trip');
    }
  }
}

export const tripsClient = new TripsClient();
```

### Search Integration with MCP Backend
```typescript
// In frontend/src/hooks/use-flight-search.ts
import { useState } from 'react';
import { authClient } from '@/lib/api/auth-client';

interface FlightSearchParams {
  origin: string;
  destination: string;
  departure_date: string;
  return_date?: string;
  passengers: number;
}

export function useFlightSearch() {
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState([]);
  const [error, setError] = useState<string | null>(null);

  const searchFlights = async (params: FlightSearchParams) => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await authClient.authenticatedFetch('/api/search/flights', {
        method: 'POST',
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        throw new Error('Flight search failed');
      }

      const data = await response.json();
      setResults(data.flights || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setIsLoading(false);
    }
  };

  return {
    searchFlights,
    results,
    isLoading,
    error,
    clearResults: () => setResults([]),
    clearError: () => setError(null),
  };
}
```

## Testing Requirements
- **Unit tests** for React components and hooks (≥90% coverage target)
- **Integration tests** for API client connections and data flow
- **E2E tests** for complete user workflows (registration to trip completion)
- **Performance tests** for page load times and API response times
- **Accessibility tests** for WCAG compliance
- **Visual regression tests** for UI consistency
- **Mobile responsiveness tests** for various device sizes
- **Error boundary tests** for graceful failure handling

## Success Criteria
1. ✅ **Authentication Flow**: Complete user registration, login, and session management
2. ✅ **Real-time Chat**: AI agents respond with live tool calling and streaming
3. ✅ **Trip Planning**: Full workflow from search to booking with data persistence
4. ✅ **API Integration**: All frontend features connect to live backend services
5. ✅ **User Experience**: Responsive, accessible, and performant interface
6. ✅ **Error Handling**: Graceful degradation and helpful error messages
7. ✅ **Performance**: Page loads under 3 seconds, API responses under 5 seconds
8. ✅ **Quality**: All tests pass with **≥90% coverage**

## Important Notes
- Build on existing Next.js App Router patterns in `frontend/src/app/`
- Use established Zustand store patterns for state management
- Implement progressive enhancement for offline functionality
- Ensure mobile-first responsive design
- Plan for internationalization (i18n) support
- Run `npx biome check --fix .` and `npx biome format --write .` on TypeScript files
- Follow existing component patterns in `frontend/src/components/`

## Frontend-Backend Integration Strategy

### API Integration Approach
1. **Authentication First**: Establish secure token-based auth flow
2. **Incremental Connection**: Connect components one feature at a time
3. **Error Resilience**: Implement comprehensive error handling and retry logic
4. **Performance Focus**: Optimize API calls with caching and pagination
5. **Real-time Features**: Add WebSocket/SSE for live updates

### State Management Patterns
1. **Server State**: Use React Query/SWR for API data caching
2. **Client State**: Use Zustand for UI state and user preferences
3. **Form State**: Use React Hook Form for complex form validation
4. **Authentication State**: Centralized auth store with token management
5. **Error State**: Global error handling with user-friendly messages

### User Experience Priorities
1. **Loading States**: Skeleton screens and progressive loading
2. **Error Boundaries**: Graceful failure with recovery options
3. **Accessibility**: ARIA labels, keyboard navigation, screen reader support
4. **Mobile Responsiveness**: Touch-friendly interface on all devices
5. **Performance**: Code splitting, image optimization, bundle size monitoring

## MCP Integration Quick Reference

### Frontend API Calls
```bash
# Authentication endpoints
POST /auth/login
POST /auth/register  
POST /auth/refresh
DELETE /auth/logout

# Trip management endpoints
GET /trips
POST /trips
PATCH /trips/{id}
DELETE /trips/{id}

# Search endpoints (MCP-powered)
POST /search/flights
POST /search/accommodations
POST /search/destinations
POST /search/activities
```

### Real-time Communication
```bash
# WebSocket connection
WS /ws?token={jwt_token}

# Server-Sent Events
GET /events/stream?token={jwt_token}

# Chat endpoints
POST /chat/message
GET /chat/history/{session_id}
```

### Performance Optimization
```bash
# When you need bundle analysis
exa__web_search_exa --query "Next.js bundle optimization techniques 2024" --numResults 5

# When you need performance analysis
sequential-thinking__sequentialthinking --thought "Analyzing frontend performance bottlenecks..." --totalThoughts 5
```

## References
- **Phase 5**: Database Integration & Chat Agent Enhancement (completed)
- **Frontend Structure**: `frontend/src/` for existing component patterns
- **API Endpoints**: `tripsage/api/routers/` for backend integration points
- **Testing Patterns**: `frontend/src/__tests__/` for established test approaches
- **State Management**: `frontend/src/stores/` for Zustand patterns

## Getting Started
1. **Research First**: Use MCP tools to understand current frontend integration best practices
2. **Examine Frontend**: Read existing components and identify integration points
3. **Plan with TODO Tools**: Create comprehensive TODO list using TodoWrite before coding
4. **Implement Incrementally**: Start with authentication, then real-time features
5. **Test Thoroughly**: Target ≥90% coverage with comprehensive E2E tests

Focus on creating a seamless, performant user experience that showcases the full power of the TripSage AI travel planning platform while maintaining clean, maintainable frontend architecture.

---

## Implementation Phases Summary

### Phase 6.1: Authentication & User Management (Week 1)
- Integrate JWT authentication with FastAPI backend
- Implement protected routes and session management
- Connect user profile and API key management components
- Add comprehensive auth flow testing

### Phase 6.2: Real-time Chat Integration (Week 2)  
- Connect chat interface to backend AI agents
- Implement WebSocket/SSE for streaming responses
- Add tool calling UI and conversation persistence
- Integrate file attachments with chat system

### Phase 6.3: Trip Planning & Data Persistence (Week 3)
- Connect trip management to backend APIs
- Implement live data integration with MCP services
- Add trip saving, editing, and sharing features
- Create budget tracking with real-time updates

### Phase 6.4: Search Components & Live Data (Week 4)
- Integrate search components with MCP backend services
- Add real-time search results and caching
- Implement search filters and result management
- Connect price tracking and alerts

### Phase 6.5: User Experience Enhancements (Week 5)
- Implement responsive design and accessibility features
- Add loading states, error handling, and offline mode
- Create onboarding flow and user guidance
- Add notifications and user feedback systems

### Phase 6.6: Testing & Performance Optimization (Week 6)
- Complete comprehensive E2E test suite (≥90% coverage)
- Add performance monitoring and optimization
- Implement visual regression testing
- Validate mobile responsiveness and accessibility

The implementation provides a complete, production-ready frontend that seamlessly integrates with the TripSage backend, delivering an exceptional user experience for AI-powered travel planning.