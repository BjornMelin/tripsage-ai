# 💻 TripSage Frontend Development Guide

> **Status**: ✅ **Production Ready** - Next.js 15.3 + React 19 Implementation  
> **Architecture**: Modern AI-centric travel planning interface  
> **Performance**: >95 Lighthouse score, <1.5s load times

This comprehensive guide covers the architecture, technology stack, development patterns, and implementation details for TripSage's frontend application.

## 📋 Table of Contents

- [Technology Stack Overview](#-technology-stack-overview)
- [Architecture and Design Patterns](#️-architecture-and-design-patterns)
- [Application Structure](#-application-structure)
- [Pages and Features](#-pages-and-features)
- [Component Development](#-component-development)
- [State Management](#️-state-management)
- [AI Integration](#-ai-integration)
- [Authentication and Security](#-authentication-and-security)
- [Performance Optimization](#-performance-optimization)
- [Testing Strategy](#-testing-strategy)
- [Development Workflow](#-development-workflow)
- [Budget-Focused Features](#-budget-focused-features)

## 🚀 Technology Stack Overview

### **Core Technologies**

#### **Framework and Runtime**

- **Next.js 15.3.1**: App Router, Server Components, API routes, Turbopack
- **React 19.1.0**: Server Components, improved Suspense, concurrent features
- **TypeScript 5.5+**: Strict type safety, template literal types
- **Node.js 20+**: Latest LTS with native ESM support

#### **UI Framework and Styling**

- **Tailwind CSS v4.0**: OKLCH color space, CSS-based config, container queries
- **shadcn/ui v3**: Copy-paste components built on Radix UI
- **Framer Motion v11**: Modern animations and transitions
- **Lucide Icons**: Consistent icon library
- **clsx & tailwind-merge**: Conditional styling utilities

#### **State Management**

- **Zustand v5.0.4**: Simple state management with native `useSyncExternalStore`
- **TanStack Query v5**: Server state, caching, and data synchronization
- **React Context API**: For isolated state within feature boundaries

#### **AI Integration**

- **Vercel AI SDK v4.3.16**: ✅ **IMPLEMENTED** - Streaming AI responses, tool calling, file attachments
- **Server-Sent Events (SSE)**: Real-time AI streaming
- **OpenAI SDK**: Direct API integration when needed
- **Custom useChatAi Hook**: Zustand integration with AI SDK for state management

#### **Form Handling and Validation**

- **React Hook Form v8**: Performance-optimized form handling
- **Zod v3**: TypeScript-first schema validation

#### **Additional Libraries**

- **Supabase JS Client**: Database integration and authentication
- **Recharts**: Data visualization
- **date-fns**: Date manipulation
- **React Email**: Email templates
- **React Hot Toast**: Notifications
- **Mapbox GL JS v3**: Interactive maps

### **Key Architecture Decisions**

#### **1. Authentication Strategy: Supabase Auth**

```typescript
// Server-side authentication with cookies
const supabase = createServerClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
  { cookies }
)

// Middleware protection for authenticated routes
export async function middleware(request: NextRequest) {
  const { supabase, response } = createServerClient(request)
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  return response
}
```

#### **2. Real-time Communication: Server-Sent Events (SSE)**

```typescript
// AI streaming via Vercel AI SDK
const { messages, input, handleSubmit, isLoading } = useChat({
  api: '/api/agents/travel-planner/stream',
  streamProtocol: 'data-stream',
  onFinish: (message) => {
    // Handle completed AI response
  },
  onError: (error) => {
    // Handle streaming errors
  }
})
```

#### **3. API Key Management: Backend Proxy Pattern**

```typescript
// Frontend → FastAPI → MCP Servers
const searchFlights = async (searchParams: FlightSearchParams) => {
  const response = await fetch('/api/mcp/flights/search', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(searchParams)
  })
  
  if (!response.ok) {
    throw new Error('Flight search failed')
  }
  
  return response.json()
}
```

## 🏗️ Architecture and Design Patterns

### **Application Architecture Overview**

```plaintext
┌──────────────────────────────────────────────────────────────────────┐
│                       Next.js 15 Application                        │
├─────────────────────────┬────────────────────────────────────────────┤
│                         │                                            │
│  ┌─────────────────────▼─────────────────┐  ┌─────────────────────▼─┐
│  │    Client Components                   │  │   Server Components  │
│  │    (Interactive UI)                    │  │   (SSR + Data)       │
│  │                                        │  │                       │
│  │  • Chat Interface                      │  │  • Authentication     │
│  │  • Search Forms                        │  │  • Data Fetching      │
│  │  • Interactive Maps                    │  │  • SEO Optimization   │
│  │  • State Management                    │  │  • Initial Render     │
│  └────────────────────────────────────────┘  └───────────────────────┘
│                         │                                            │
└─────────────────────────┼────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────┐
│                      State Management Layer                         │
│  ┌───────────────┐  ┌───────────────┐  ┌─────────────────────────┐  │
│  │   Zustand     │  │ TanStack      │  │    React Context        │  │
│  │   (Client)    │  │ Query         │  │    (Feature Scoped)     │  │
│  │               │  │ (Server)      │  │                         │  │
│  └───────────────┘  └───────────────┘  └─────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
                          │
┌─────────────────────────▼────────────────────────────────────────────┐
│                      API Integration Layer                          │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │                 Next.js API Routes                              │  │
│  │                 (Proxy to FastAPI)                              │  │
│  └─────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### **Component Architecture Patterns**

#### **1. Feature-Based Organization**

```typescript
// Feature-based directory structure
src/
├── components/
│   ├── features/
│   │   ├── chat/           # Chat-related components
│   │   ├── search/         # Search functionality
│   │   ├── trips/          # Trip management
│   │   ├── profile/        # User profile
│   │   └── dashboard/      # Dashboard widgets
│   ├── ui/                 # Reusable UI components
│   └── layouts/            # Layout components
├── hooks/                  # Custom React hooks
├── stores/                 # Zustand stores
├── types/                  # TypeScript types
└── lib/                    # Utilities and services
```

#### **2. Compound Component Pattern**

```typescript
// Example: Search component with sub-components
export const SearchInterface = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="search-interface">
      {children}
    </div>
  )
}

SearchInterface.Form = SearchForm
SearchInterface.Results = SearchResults
SearchInterface.Filters = SearchFilters
SearchInterface.Pagination = SearchPagination

// Usage
<SearchInterface>
  <SearchInterface.Form />
  <SearchInterface.Filters />
  <SearchInterface.Results />
  <SearchInterface.Pagination />
</SearchInterface>
```

#### **3. Render Props Pattern for AI Integration**

```typescript
// AI Chat component with render props
interface ChatProviderProps {
  children: (chatState: ChatState) => React.ReactNode
}

export const ChatProvider = ({ children }: ChatProviderProps) => {
  const { messages, input, handleSubmit, isLoading } = useChat({
    api: '/api/agents/travel-planner/stream'
  })
  
  return children({
    messages,
    input,
    handleSubmit,
    isLoading,
    // Additional chat utilities
  })
}

// Usage
<ChatProvider>
  {({ messages, input, handleSubmit, isLoading }) => (
    <>
      <MessageList messages={messages} />
      <MessageInput 
        value={input} 
        onSubmit={handleSubmit}
        disabled={isLoading}
      />
    </>
  )}
</ChatProvider>
```

## 📱 Application Structure

### **Directory Structure**

```plaintext
frontend/
├── src/
│   ├── app/                           # Next.js App Router pages
│   │   ├── (auth)/                    # Authentication pages group
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── reset-password/
│   │   ├── (dashboard)/               # Dashboard pages group
│   │   │   ├── page.tsx               # Dashboard home
│   │   │   ├── trips/
│   │   │   ├── search/
│   │   │   ├── chat/
│   │   │   ├── profile/
│   │   │   └── settings/
│   │   ├── api/                       # API routes
│   │   │   ├── auth/
│   │   │   ├── chat/
│   │   │   └── mcp/
│   │   ├── globals.css
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/
│   │   ├── features/                  # Feature-specific components
│   │   │   ├── chat/
│   │   │   │   ├── chat-interface.tsx
│   │   │   │   ├── message-list.tsx
│   │   │   │   ├── message-input.tsx
│   │   │   │   └── typing-indicator.tsx
│   │   │   ├── search/
│   │   │   │   ├── flight-search-form.tsx
│   │   │   │   ├── hotel-search-form.tsx
│   │   │   │   ├── search-results.tsx
│   │   │   │   └── search-filters.tsx
│   │   │   ├── trips/
│   │   │   │   ├── trip-card.tsx
│   │   │   │   ├── trip-timeline.tsx
│   │   │   │   ├── budget-tracker.tsx
│   │   │   │   └── itinerary-builder.tsx
│   │   │   ├── profile/
│   │   │   │   ├── personal-info-section.tsx
│   │   │   │   ├── preferences-section.tsx
│   │   │   │   ├── security-section.tsx
│   │   │   │   └── account-settings-section.tsx
│   │   │   └── dashboard/
│   │   │       ├── quick-actions.tsx
│   │   │       ├── recent-trips.tsx
│   │   │       ├── trip-suggestions.tsx
│   │   │       └── upcoming-flights.tsx
│   │   ├── ui/                        # Reusable UI components
│   │   │   ├── button.tsx
│   │   │   ├── input.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── form.tsx
│   │   │   ├── loading-spinner.tsx
│   │   │   ├── skeleton.tsx
│   │   │   └── toast.tsx
│   │   ├── layouts/
│   │   │   ├── auth-layout.tsx
│   │   │   ├── dashboard-layout.tsx
│   │   │   ├── chat-layout.tsx
│   │   │   └── search-layout.tsx
│   │   └── providers/
│   │       ├── query-provider.tsx
│   │       └── theme-provider.tsx
│   ├── hooks/                         # Custom React hooks
│   │   ├── use-chat-ai.ts
│   │   ├── use-websocket.ts
│   │   ├── use-search.ts
│   │   ├── use-budget.ts
│   │   ├── use-currency.ts
│   │   └── use-api-keys.ts
│   ├── stores/                        # Zustand stores
│   │   ├── chat-store.ts
│   │   ├── search-store.ts
│   │   ├── trip-store.ts
│   │   ├── user-store.ts
│   │   ├── budget-store.ts
│   │   ├── currency-store.ts
│   │   └── api-key-store.ts
│   ├── types/                         # TypeScript type definitions
│   │   ├── chat.ts
│   │   ├── search.ts
│   │   ├── trips.ts
│   │   ├── budget.ts
│   │   ├── currency.ts
│   │   ├── api-keys.ts
│   │   └── auth.ts
│   ├── lib/                           # Utilities and services
│   │   ├── api/
│   │   │   ├── client.ts
│   │   │   └── chat-api.ts
│   │   ├── utils.ts
│   │   ├── websocket/
│   │   │   └── websocket-client.ts
│   │   └── hooks/
│   │       ├── use-search.ts
│   │       ├── use-budget.ts
│   │       └── use-memory.ts
│   └── middleware.ts                   # Next.js middleware
├── public/
│   ├── icons/
│   ├── images/
│   └── manifests/
├── package.json
├── next.config.ts
├── tailwind.config.js
├── tsconfig.json
├── biome.json
├── playwright.config.ts
└── vitest.config.ts
```

## 🌐 Pages and Features

### **Core Navigation Structure**

```plaintext
TripSage
├── Public Pages
│   ├── Landing Page (/)
│   ├── Login (/login)
│   ├── Register (/register)
│   └── Password Reset (/reset-password)
│
└── Dashboard (Authenticated)
    ├── Overview (/dashboard)
    ├── Trips (/dashboard/trips)
    │   ├── All Trips (/dashboard/trips)
    │   ├── Trip Details (/dashboard/trips/[id])
    │   └── Create Trip (/dashboard/trips/new)
    ├── Search (/dashboard/search)
    │   ├── Flights (/dashboard/search/flights)
    │   ├── Hotels (/dashboard/search/hotels)
    │   ├── Activities (/dashboard/search/activities)
    │   └── Destinations (/dashboard/search/destinations)
    ├── AI Chat (/dashboard/chat)
    │   ├── Active Chat (/dashboard/chat)
    │   └── Chat History (/dashboard/chat/[sessionId])
    ├── Agent Status (/dashboard/agent-status)
    ├── Analytics (/dashboard/analytics)
    ├── Profile (/dashboard/profile)
    └── Settings (/dashboard/settings)
        ├── API Keys (/dashboard/settings/api-keys)
        ├── Preferences (/dashboard/settings/preferences)
        └── Notifications (/dashboard/settings/notifications)
```

### **Page Implementation Examples**

#### **1. Dashboard Overview (`/dashboard`)**

```typescript
// app/(dashboard)/page.tsx
import { Suspense } from 'react'
import { QuickActions } from '@/components/features/dashboard/quick-actions'
import { RecentTrips } from '@/components/features/dashboard/recent-trips'
import { TripSuggestions } from '@/components/features/dashboard/trip-suggestions'
import { UpcomingFlights } from '@/components/features/dashboard/upcoming-flights'
import { DashboardSkeleton } from '@/components/ui/loading-skeletons'

export default function DashboardPage() {
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <div className="md:col-span-2">
        <QuickActions />
      </div>
      <div className="space-y-6">
        <Suspense fallback={<DashboardSkeleton />}>
          <UpcomingFlights />
        </Suspense>
        <Suspense fallback={<DashboardSkeleton />}>
          <TripSuggestions />
        </Suspense>
      </div>
      <div className="md:col-span-2 lg:col-span-3">
        <Suspense fallback={<DashboardSkeleton />}>
          <RecentTrips />
        </Suspense>
      </div>
    </div>
  )
}
```

#### **2. AI Chat Interface (`/dashboard/chat`)**

```typescript
// app/(dashboard)/chat/page.tsx
import { ChatInterface } from '@/components/features/chat/chat-interface'
import { ChatProvider } from '@/lib/providers/chat-provider'

export default function ChatPage() {
  return (
    <ChatProvider>
      <div className="flex h-full flex-col">
        <div className="border-b p-4">
          <h1 className="text-2xl font-semibold">AI Travel Assistant</h1>
          <p className="text-muted-foreground">
            Get personalized travel recommendations and assistance
          </p>
        </div>
        <ChatInterface />
      </div>
    </ChatProvider>
  )
}
```

#### **3. Flight Search (`/dashboard/search/flights`)**

```typescript
// app/(dashboard)/search/flights/page.tsx
import { FlightSearchForm } from '@/components/features/search/flight-search-form'
import { SearchResults } from '@/components/features/search/search-results'
import { SearchFilters } from '@/components/features/search/search-filters'
import { useSearchStore } from '@/stores/search-store'

export default function FlightSearchPage() {
  const { searchResults, isLoading, filters } = useSearchStore()
  
  return (
    <div className="grid gap-6 md:grid-cols-4">
      <div className="md:col-span-3">
        <FlightSearchForm />
        {searchResults && (
          <SearchResults 
            results={searchResults}
            isLoading={isLoading}
          />
        )}
      </div>
      <div className="space-y-4">
        <SearchFilters filters={filters} />
      </div>
    </div>
  )
}
```

## 🧩 Component Development

### **Component Design Principles**

#### **1. Single Responsibility**

```typescript
// ✅ Good: Component has single responsibility
export const MessageBubble = ({ message, isUser }: MessageBubbleProps) => {
  return (
    <div className={cn(
      "flex w-max max-w-[75%] flex-col gap-2 rounded-lg px-3 py-2 text-sm",
      isUser 
        ? "ml-auto bg-primary text-primary-foreground" 
        : "bg-muted"
    )}>
      <p>{message.content}</p>
      <time className="text-xs opacity-50">
        {formatTime(message.timestamp)}
      </time>
    </div>
  )
}

// ❌ Bad: Component doing too many things
export const MessageComponent = ({ message, isUser, onEdit, onDelete, onReply }) => {
  // Too many responsibilities
}
```

#### **2. Composition over Configuration**

```typescript
// ✅ Good: Composable components
export const Card = ({ children, className, ...props }: CardProps) => (
  <div className={cn("rounded-lg border bg-card text-card-foreground shadow-sm", className)} {...props}>
    {children}
  </div>
)

export const CardHeader = ({ children, className, ...props }: CardHeaderProps) => (
  <div className={cn("flex flex-col space-y-1.5 p-6", className)} {...props}>
    {children}
  </div>
)

export const CardContent = ({ children, className, ...props }: CardContentProps) => (
  <div className={cn("p-6 pt-0", className)} {...props}>
    {children}
  </div>
)

// Usage
<Card>
  <CardHeader>
    <h3>Trip to Paris</h3>
  </CardHeader>
  <CardContent>
    <p>5 days, 4 nights</p>
  </CardContent>
</Card>
```

#### **3. TypeScript-First Development**

```typescript
// Comprehensive type definitions
interface TripCardProps {
  trip: Trip
  variant?: 'default' | 'compact' | 'detailed'
  onEdit?: (tripId: string) => void
  onDelete?: (tripId: string) => void
  onShare?: (tripId: string) => void
  showActions?: boolean
  className?: string
}

interface Trip {
  id: string
  title: string
  destination: string
  startDate: Date
  endDate: Date
  budget?: Budget
  status: TripStatus
  participants: Participant[]
  itinerary: ItineraryItem[]
  createdAt: Date
  updatedAt: Date
}

// Component with full type safety
export const TripCard = ({ 
  trip, 
  variant = 'default',
  onEdit,
  onDelete,
  onShare,
  showActions = true,
  className 
}: TripCardProps) => {
  // Implementation with full IntelliSense support
}
```

### **Component Testing Strategy**

#### **1. Unit Testing with Vitest**

```typescript
// components/ui/button.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { Button } from './button'

describe('Button', () => {
  it('renders children correctly', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button')).toHaveTextContent('Click me')
  })
  
  it('handles click events', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    fireEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })
  
  it('applies variant styles correctly', () => {
    render(<Button variant="destructive">Delete</Button>)
    expect(screen.getByRole('button')).toHaveClass('bg-destructive')
  })
})
```

#### **2. Integration Testing with Playwright**

```typescript
// e2e/chat-interface.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard/chat')
  })
  
  test('should send message and receive AI response', async ({ page }) => {
    // Type message
    await page.fill('[data-testid="message-input"]', 'Plan a trip to Tokyo')
    await page.click('[data-testid="send-button"]')
    
    // Wait for AI response
    await expect(page.locator('[data-testid="ai-message"]').first()).toBeVisible()
    
    // Verify response contains relevant content
    const response = await page.locator('[data-testid="ai-message"]').first().textContent()
    expect(response).toContain('Tokyo')
  })
})
```

## 🗂️ State Management

### **Zustand Store Architecture**

#### **1. Chat Store**

```typescript
// stores/chat-store.ts
import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import type { Message, ChatSession } from '@/types/chat'

interface ChatState {
  // State
  currentSession: ChatSession | null
  sessions: ChatSession[]
  isLoading: boolean
  error: string | null
  
  // Actions
  createSession: () => Promise<ChatSession>
  switchSession: (sessionId: string) => Promise<void>
  sendMessage: (content: string, attachments?: File[]) => Promise<void>
  clearError: () => void
  deleteSession: (sessionId: string) => Promise<void>
}

export const useChatStore = create<ChatState>()(
  subscribeWithSelector(
    (set, get) => ({
      // Initial state
      currentSession: null,
      sessions: [],
      isLoading: false,
      error: null,
      
      // Actions
      createSession: async () => {
        set({ isLoading: true })
        try {
          const session = await chatApi.createSession()
          set(state => ({
            sessions: [...state.sessions, session],
            currentSession: session,
            isLoading: false
          }))
          return session
        } catch (error) {
          set({ error: error.message, isLoading: false })
          throw error
        }
      },
      
      switchSession: async (sessionId: string) => {
        const session = get().sessions.find(s => s.id === sessionId)
        if (session) {
          set({ currentSession: session })
        } else {
          // Load from server
          set({ isLoading: true })
          try {
            const session = await chatApi.getSession(sessionId)
            set({ currentSession: session, isLoading: false })
          } catch (error) {
            set({ error: error.message, isLoading: false })
          }
        }
      },
      
      sendMessage: async (content: string, attachments?: File[]) => {
        const { currentSession } = get()
        if (!currentSession) throw new Error('No active session')
        
        set({ isLoading: true })
        try {
          const response = await chatApi.sendMessage(currentSession.id, {
            content,
            attachments
          })
          
          set(state => ({
            currentSession: {
              ...state.currentSession!,
              messages: [...state.currentSession!.messages, response.userMessage, response.aiMessage]
            },
            isLoading: false
          }))
        } catch (error) {
          set({ error: error.message, isLoading: false })
        }
      },
      
      clearError: () => set({ error: null }),
      
      deleteSession: async (sessionId: string) => {
        try {
          await chatApi.deleteSession(sessionId)
          set(state => ({
            sessions: state.sessions.filter(s => s.id !== sessionId),
            currentSession: state.currentSession?.id === sessionId ? null : state.currentSession
          }))
        } catch (error) {
          set({ error: error.message })
        }
      }
    })
  )
)

// Selectors for optimized re-renders
export const useCurrentSession = () => useChatStore(state => state.currentSession)
export const useChatLoading = () => useChatStore(state => state.isLoading)
export const useChatError = () => useChatStore(state => state.error)
```

#### **2. Search Store**

```typescript
// stores/search-store.ts
interface SearchState {
  // Flight search
  flightSearchParams: FlightSearchParams | null
  flightResults: FlightResult[]
  
  // Hotel search
  hotelSearchParams: HotelSearchParams | null
  hotelResults: HotelResult[]
  
  // Search state
  isSearching: boolean
  searchType: 'flights' | 'hotels' | 'activities' | null
  filters: SearchFilters
  
  // Actions
  searchFlights: (params: FlightSearchParams) => Promise<void>
  searchHotels: (params: HotelSearchParams) => Promise<void>
  updateFilters: (filters: Partial<SearchFilters>) => void
  clearResults: () => void
  saveSearch: (searchId: string) => Promise<void>
}

export const useSearchStore = create<SearchState>((set, get) => ({
  // State implementation
  flightSearchParams: null,
  flightResults: [],
  hotelSearchParams: null,
  hotelResults: [],
  isSearching: false,
  searchType: null,
  filters: DEFAULT_FILTERS,
  
  // Actions
  searchFlights: async (params: FlightSearchParams) => {
    set({ isSearching: true, searchType: 'flights', flightSearchParams: params })
    
    try {
      const results = await searchApi.searchFlights(params)
      set({ 
        flightResults: results,
        isSearching: false 
      })
    } catch (error) {
      set({ isSearching: false })
      throw error
    }
  },
  
  // Additional actions...
}))
```

### **TanStack Query Integration**

#### **Server State Management**

```typescript
// hooks/use-trips.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { tripApi } from '@/lib/api/trip-api'

export const useTrips = () => {
  return useQuery({
    queryKey: ['trips'],
    queryFn: tripApi.getTrips,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

export const useTrip = (tripId: string) => {
  return useQuery({
    queryKey: ['trip', tripId],
    queryFn: () => tripApi.getTrip(tripId),
    enabled: !!tripId,
  })
}

export const useCreateTrip = () => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: tripApi.createTrip,
    onSuccess: (newTrip) => {
      // Update trips list cache
      queryClient.setQueryData(['trips'], (old: Trip[] = []) => [...old, newTrip])
      
      // Prefetch trip details
      queryClient.setQueryData(['trip', newTrip.id], newTrip)
    },
  })
}

export const useUpdateTrip = (tripId: string) => {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: (updates: Partial<Trip>) => tripApi.updateTrip(tripId, updates),
    onSuccess: (updatedTrip) => {
      // Update specific trip cache
      queryClient.setQueryData(['trip', tripId], updatedTrip)
      
      // Update trips list cache
      queryClient.setQueryData(['trips'], (old: Trip[] = []) =>
        old.map(trip => trip.id === tripId ? updatedTrip : trip)
      )
    },
  })
}
```

## 🤖 AI Integration

### **Vercel AI SDK Implementation**

#### **1. Chat Hook with Streaming**

```typescript
// hooks/use-chat-ai.ts
import { useChat } from 'ai/react'
import { useChatStore } from '@/stores/chat-store'

export const useChatAI = (sessionId?: string) => {
  const { currentSession, updateSession } = useChatStore()
  
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    error,
    reload,
    stop,
    append,
    setMessages
  } = useChat({
    api: `/api/chat/${sessionId || currentSession?.id}`,
    streamProtocol: 'data-stream',
    
    onResponse: (response) => {
      console.log('AI response received:', response.status)
    },
    
    onFinish: (message) => {
      // Update chat store with completed message
      updateSession(currentSession!.id, {
        messages: [...messages, message]
      })
    },
    
    onError: (error) => {
      console.error('Chat error:', error)
      // Handle error in UI
    }
  })
  
  // Enhanced submit with file attachments
  const submitWithAttachments = async (
    message: string, 
    attachments?: File[]
  ) => {
    if (attachments?.length) {
      // Upload attachments first
      const uploadedAttachments = await uploadAttachments(attachments)
      
      await append({
        role: 'user',
        content: message,
        experimental_attachments: uploadedAttachments
      })
    } else {
      await handleSubmit()
    }
  }
  
  return {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    submitWithAttachments,
    isLoading,
    error,
    reload,
    stop,
    setMessages
  }
}
```

#### **2. API Route for AI Streaming**

```typescript
// app/api/chat/[sessionId]/route.ts
import { NextRequest } from 'next/server'
import { streamText } from 'ai'
import { openai } from '@/lib/openai'
import { auth } from '@/lib/auth'

export async function POST(
  req: NextRequest,
  { params }: { params: { sessionId: string } }
) {
  try {
    const { user } = await auth()
    if (!user) {
      return new Response('Unauthorized', { status: 401 })
    }
    
    const { messages, attachments } = await req.json()
    const { sessionId } = params
    
    // Get chat session and context
    const session = await getChatSession(sessionId, user.id)
    if (!session) {
      return new Response('Session not found', { status: 404 })
    }
    
    // Prepare system prompt with context
    const systemPrompt = await buildSystemPrompt(user, session)
    
    // Stream AI response
    const result = await streamText({
      model: openai('gpt-4-turbo'),
      system: systemPrompt,
      messages: [
        ...session.previousMessages.slice(-10), // Last 10 messages for context
        ...messages
      ],
      attachments,
      tools: {
        searchFlights: {
          description: 'Search for flights',
          parameters: z.object({
            origin: z.string(),
            destination: z.string(),
            departDate: z.string(),
            returnDate: z.string().optional(),
            passengers: z.number().default(1)
          }),
          execute: async (params) => {
            return await searchFlights(params, user.apiKeys)
          }
        },
        searchHotels: {
          description: 'Search for hotels',
          parameters: z.object({
            location: z.string(),
            checkIn: z.string(),
            checkOut: z.string(),
            guests: z.number().default(2)
          }),
          execute: async (params) => {
            return await searchHotels(params, user.apiKeys)
          }
        },
        // Additional tools...
      },
      maxTokens: 2000,
      temperature: 0.7,
    })
    
    // Save conversation to database
    await saveChatInteraction(sessionId, messages, result)
    
    return result.toDataStreamResponse()
    
  } catch (error) {
    console.error('Chat API error:', error)
    return new Response('Internal Server Error', { status: 500 })
  }
}
```

### **Tool Calling Integration**

#### **Travel Planning Tools**

```typescript
// lib/ai/travel-tools.ts
export const travelPlanningTools = {
  searchFlights: {
    description: 'Search for flights between cities',
    parameters: z.object({
      origin: z.string().describe('Origin city or airport code'),
      destination: z.string().describe('Destination city or airport code'),
      departDate: z.string().describe('Departure date (YYYY-MM-DD)'),
      returnDate: z.string().optional().describe('Return date (YYYY-MM-DD)'),
      passengers: z.number().default(1).describe('Number of passengers'),
      class: z.enum(['economy', 'premium_economy', 'business', 'first']).default('economy')
    }),
    execute: async (params: FlightSearchParams, userContext: UserContext) => {
      try {
        const results = await flightService.search({
          ...params,
          apiKeys: userContext.apiKeys
        })
        
        return {
          success: true,
          flights: results.flights.slice(0, 5), // Top 5 results
          searchId: results.searchId,
          totalResults: results.totalResults
        }
      } catch (error) {
        return {
          success: false,
          error: error.message
        }
      }
    }
  },
  
  getWeatherForecast: {
    description: 'Get weather forecast for a destination',
    parameters: z.object({
      location: z.string().describe('City or location name'),
      dates: z.array(z.string()).describe('Dates to check (YYYY-MM-DD format)')
    }),
    execute: async (params: WeatherParams, userContext: UserContext) => {
      const weather = await weatherService.getForecast({
        location: params.location,
        dates: params.dates,
        apiKey: userContext.apiKeys.openweathermap
      })
      
      return {
        location: params.location,
        forecast: weather.daily,
        travelRecommendations: weather.travelAdvice
      }
    }
  },
  
  findAccommodations: {
    description: 'Search for hotels and accommodations',
    parameters: z.object({
      destination: z.string().describe('Destination city'),
      checkIn: z.string().describe('Check-in date (YYYY-MM-DD)'),
      checkOut: z.string().describe('Check-out date (YYYY-MM-DD)'),
      guests: z.number().default(2).describe('Number of guests'),
      maxPrice: z.number().optional().describe('Maximum price per night'),
      amenities: z.array(z.string()).optional().describe('Required amenities')
    }),
    execute: async (params: AccommodationSearchParams, userContext: UserContext) => {
      const results = await accommodationService.search({
        ...params,
        providers: ['airbnb', 'booking'],
        apiKeys: userContext.apiKeys
      })
      
      return {
        accommodations: results.accommodations.slice(0, 8),
        totalResults: results.totalResults,
        averagePrice: results.averagePrice
      }
    }
  }
}
```

## 🔐 Authentication and Security

### **Authentication Implementation Status (June 6, 2025)**

**✅ Completed Security Foundations:**

- **JWT Security Hardening**: Critical vulnerabilities resolved - hardcoded fallback secrets removed from production code
- **Frontend Authentication Foundation**: Production-ready JWT middleware and React 19 Server Actions implemented
- **Security Architecture**: HttpOnly cookies, strict environment validation, comprehensive input validation with Zod

**🔄 Integration Requirements:**

- **Backend Connection**: Frontend JWT system ready for FastAPI service integration
- **Token Refresh**: Secure refresh mechanism implemented, requires backend endpoint connection
- **User Session Management**: Complete session handling infrastructure ready for activation

### **JWT-Based Authentication Architecture**

The current implementation uses a production-ready JWT system with React 19 Server Actions:

```typescript
// Frontend JWT Implementation (middleware.ts & server-actions.ts)
// ✅ SECURITY HARDENED - No fallback secrets in production
if (!process.env.JWT_SECRET) {
  throw new Error(
    "SECURITY ERROR: JWT_SECRET environment variable is required. " +
    "Generate one using: openssl rand -base64 32"
  );
}

// Secure JWT token creation and validation
export async function createJWT(payload: Omit<JWTPayload, "iat" | "exp">) {
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + 60 * 60 * 24 * 7; // 7 days

  return await new SignJWT({ ...payload, iat, exp })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt(iat)
    .setExpirationTime(exp)
    .sign(JWT_SECRET);
}
```

### **Supabase Authentication Setup (Alternative Implementation)**

#### **1. Authentication Provider**

```typescript
// lib/auth/supabase.ts
import { createServerClient, type CookieOptions } from '@supabase/ssr'
import { cookies } from 'next/headers'

export const createClient = () => {
  const cookieStore = cookies()

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return cookieStore.get(name)?.value
        },
        set(name: string, value: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value, ...options })
          } catch (error) {
            // Handle cookie setting errors
          }
        },
        remove(name: string, options: CookieOptions) {
          try {
            cookieStore.set({ name, value: '', ...options })
          } catch (error) {
            // Handle cookie removal errors
          }
        },
      },
    }
  )
}

export const getUser = async () => {
  const supabase = createClient()
  
  try {
    const { data: { user }, error } = await supabase.auth.getUser()
    return { user, error }
  } catch (error) {
    return { user: null, error }
  }
}
```

#### **2. Route Protection Middleware**

```typescript
// middleware.ts
import { createServerClient } from '@supabase/ssr'
import { NextResponse, type NextRequest } from 'next/server'

export async function middleware(request: NextRequest) {
  let response = NextResponse.next({
    request: {
      headers: request.headers,
    },
  })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get(name: string) {
          return request.cookies.get(name)?.value
        },
        set(name: string, value: string, options: any) {
          request.cookies.set({
            name,
            value,
            ...options,
          })
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          response.cookies.set({
            name,
            value,
            ...options,
          })
        },
        remove(name: string, options: any) {
          request.cookies.set({
            name,
            value: '',
            ...options,
          })
          response = NextResponse.next({
            request: {
              headers: request.headers,
            },
          })
          response.cookies.set({
            name,
            value: '',
            ...options,
          })
        },
      },
    }
  )

  // Get user from session
  const { data: { user } } = await supabase.auth.getUser()

  // Protect dashboard routes
  if (request.nextUrl.pathname.startsWith('/dashboard')) {
    if (!user) {
      return NextResponse.redirect(new URL('/login', request.url))
    }
  }

  // Redirect authenticated users away from auth pages
  if (request.nextUrl.pathname.startsWith('/login') || 
      request.nextUrl.pathname.startsWith('/register')) {
    if (user) {
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
  }

  return response
}

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
```

#### **3. Client-Side Auth Hook**

```typescript
// hooks/use-auth.ts
import { createClientComponentClient } from '@supabase/auth-helpers-nextjs'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import type { User } from '@supabase/supabase-js'

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const supabase = createClientComponentClient()
  const router = useRouter()

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser()
      setUser(user)
      setLoading(false)
    }

    getUser()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        setUser(session?.user || null)
        setLoading(false)
        
        if (event === 'SIGNED_IN') {
          router.push('/dashboard')
        } else if (event === 'SIGNED_OUT') {
          router.push('/login')
        }
      }
    )

    return () => subscription.unsubscribe()
  }, [supabase, router])

  const signIn = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    })
    return { data, error }
  }

  const signUp = async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
    })
    return { data, error }
  }

  const signOut = async () => {
    await supabase.auth.signOut()
  }

  const resetPassword = async (email: string) => {
    const { data, error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/reset-password`,
    })
    return { data, error }
  }

  return {
    user,
    loading,
    signIn,
    signUp,
    signOut,
    resetPassword,
  }
}
```

### **API Security**

#### **1. API Route Protection**

```typescript
// lib/api/middleware.ts
import { NextRequest, NextResponse } from 'next/server'
import { getUser } from '@/lib/auth/supabase'

export const withAuth = (handler: Function) => {
  return async (req: NextRequest, ...args: any[]) => {
    const { user, error } = await getUser()
    
    if (error || !user) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    
    return handler(req, { user }, ...args)
  }
}

export const withRateLimit = (handler: Function, limit: number = 100) => {
  const requests = new Map()
  
  return async (req: NextRequest, ...args: any[]) => {
    const ip = req.ip || 'unknown'
    const now = Date.now()
    const windowMs = 15 * 60 * 1000 // 15 minutes
    
    if (!requests.has(ip)) {
      requests.set(ip, { count: 1, resetTime: now + windowMs })
    } else {
      const userRequests = requests.get(ip)
      
      if (now > userRequests.resetTime) {
        userRequests.count = 1
        userRequests.resetTime = now + windowMs
      } else {
        userRequests.count++
      }
      
      if (userRequests.count > limit) {
        return NextResponse.json(
          { error: 'Rate limit exceeded' }, 
          { status: 429 }
        )
      }
    }
    
    return handler(req, ...args)
  }
}
```

## ⚡ Performance Optimization

### **Core Performance Strategies**

#### **1. Next.js Optimizations**

```typescript
// next.config.ts
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Performance optimizations
  compiler: {
    removeConsole: process.env.NODE_ENV === 'production',
  },
  
  // Image optimization
  images: {
    domains: ['images.unsplash.com', 'avatars.githubusercontent.com'],
    formats: ['image/webp', 'image/avif'],
  },
  
  // Bundle analyzer
  bundleAnalyzer: {
    enabled: process.env.ANALYZE === 'true',
  },
  
  // Experimental features
  experimental: {
    turbo: true,
    serverComponentsExternalPackages: ['@supabase/supabase-js'],
  },
  
  // Headers for security and performance
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
        ],
      },
    ]
  },
}

export default nextConfig
```

#### **2. Component Lazy Loading**

```typescript
// Dynamic imports for heavy components
import dynamic from 'next/dynamic'

const MapComponent = dynamic(
  () => import('@/components/features/maps/interactive-map'),
  { 
    ssr: false,
    loading: () => <MapSkeleton />
  }
)

const ChartComponent = dynamic(
  () => import('@/components/features/analytics/price-chart'),
  {
    loading: () => <ChartSkeleton />
  }
)

// Usage with conditional loading
export const TripDetails = ({ trip }: { trip: Trip }) => {
  const [showMap, setShowMap] = useState(false)
  
  return (
    <div>
      <TripHeader trip={trip} />
      <TripItinerary trip={trip} />
      
      <Button onClick={() => setShowMap(true)}>
        Show Map
      </Button>
      
      {showMap && (
        <MapComponent 
          destinations={trip.destinations}
          routes={trip.routes}
        />
      )}
    </div>
  )
}
```

#### **3. Image Optimization**

```typescript
// Optimized image component
import Image from 'next/image'

export const TripImage = ({ 
  src, 
  alt, 
  priority = false,
  className 
}: TripImageProps) => {
  return (
    <Image
      src={src}
      alt={alt}
      fill
      priority={priority}
      className={className}
      sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
      placeholder="blur"
      blurDataURL="data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCdABmX/9k="
    />
  )
}
```

#### **4. Bundle Optimization**

```typescript
// lib/utils/dynamic-imports.ts
export const dynamicImports = {
  // Heavy date libraries
  DatePicker: () => import('react-datepicker'),
  Calendar: () => import('react-big-calendar'),
  
  // Chart libraries
  LineChart: () => import('recharts').then(mod => ({ default: mod.LineChart })),
  PieChart: () => import('recharts').then(mod => ({ default: mod.PieChart })),
  
  // Map libraries
  MapGL: () => import('react-map-gl'),
  
  // Heavy UI components
  DataTable: () => import('@tanstack/react-table'),
  Editor: () => import('@monaco-editor/react'),
}

// Usage with React.lazy
const LazyDatePicker = React.lazy(dynamicImports.DatePicker)

export const DatePickerField = (props: DatePickerProps) => (
  <Suspense fallback={<InputSkeleton />}>
    <LazyDatePicker {...props} />
  </Suspense>
)
```

### **Caching Strategy**

#### **1. Client-Side Caching**

```typescript
// lib/cache/client-cache.ts
class ClientCache {
  private cache = new Map<string, { data: any; timestamp: number; ttl: number }>()
  
  set(key: string, data: any, ttl: number = 5 * 60 * 1000) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttl
    })
  }
  
  get(key: string) {
    const item = this.cache.get(key)
    if (!item) return null
    
    if (Date.now() - item.timestamp > item.ttl) {
      this.cache.delete(key)
      return null
    }
    
    return item.data
  }
  
  clear() {
    this.cache.clear()
  }
}

export const clientCache = new ClientCache()
```

## 🧪 Testing Strategy

### **Testing Architecture**

#### **1. Unit Testing with Vitest - Testing Architecture**

```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    coverage: {
      reporter: ['text', 'json', 'html'],
      threshold: {
        global: {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80,
        },
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

#### **2. Component Testing**

```typescript
// __tests__/components/trip-card.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { TripCard } from '@/components/features/trips/trip-card'
import { mockTrip } from '@/test/mocks/trip'

const renderTripCard = (props = {}) => {
  const defaultProps = {
    trip: mockTrip,
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    ...props,
  }
  
  return render(<TripCard {...defaultProps} />)
}

describe('TripCard', () => {
  it('displays trip information correctly', () => {
    renderTripCard()
    
    expect(screen.getByText(mockTrip.title)).toBeInTheDocument()
    expect(screen.getByText(mockTrip.destination)).toBeInTheDocument()
    expect(screen.getByText(/5 days/)).toBeInTheDocument()
  })
  
  it('calls onEdit when edit button is clicked', () => {
    const onEdit = vi.fn()
    renderTripCard({ onEdit })
    
    fireEvent.click(screen.getByRole('button', { name: /edit/i }))
    expect(onEdit).toHaveBeenCalledWith(mockTrip.id)
  })
  
  it('shows loading state correctly', () => {
    renderTripCard({ loading: true })
    
    expect(screen.getByTestId('trip-card-skeleton')).toBeInTheDocument()
  })
})
```

#### **3. E2E Testing with Playwright**

```typescript
// e2e/trip-creation.spec.ts
import { test, expect } from '@playwright/test'

test.describe('Trip Creation Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/login')
    await page.fill('[data-testid="email"]', 'test@example.com')
    await page.fill('[data-testid="password"]', 'password')
    await page.click('[data-testid="login-button"]')
    
    // Navigate to trip creation
    await page.goto('/dashboard/trips/new')
  })
  
  test('creates a new trip successfully', async ({ page }) => {
    // Fill trip details
    await page.fill('[data-testid="trip-title"]', 'Paris Vacation')
    await page.fill('[data-testid="destination"]', 'Paris, France')
    await page.fill('[data-testid="start-date"]', '2024-06-01')
    await page.fill('[data-testid="end-date"]', '2024-06-07')
    await page.fill('[data-testid="budget"]', '3000')
    
    // Submit form
    await page.click('[data-testid="create-trip-button"]')
    
    // Verify redirect and success
    await expect(page).toHaveURL(/\/dashboard\/trips\/\w+/)
    await expect(page.locator('[data-testid="trip-title"]')).toContainText('Paris Vacation')
  })
  
  test('validates required fields', async ({ page }) => {
    // Try to submit without required fields
    await page.click('[data-testid="create-trip-button"]')
    
    // Check for validation errors
    await expect(page.locator('[data-testid="title-error"]')).toBeVisible()
    await expect(page.locator('[data-testid="destination-error"]')).toBeVisible()
  })
})
```

## 🔄 Development Workflow

### **Development Setup**

#### **1. Project Setup Commands**

```bash
# Install dependencies
pnpm install

# Start development server
pnpm dev

# Run type checking
pnpm type-check

# Run linting
pnpm lint

# Run formatting
pnpm format

# Run tests
pnpm test
pnpm test:watch
pnpm test:coverage

# Run E2E tests
pnpm test:e2e
pnpm test:e2e:ui

# Build for production
pnpm build

# Start production server
pnpm start
```

#### **2. Git Hooks with Husky**

```json
// package.json
{
  "scripts": {
    "prepare": "husky install"
  },
  "lint-staged": {
    "*.{js,jsx,ts,tsx}": [
      "biome lint --apply",
      "biome format --write"
    ],
    "*.{json,md}": [
      "biome format --write"
    ]
  }
}
```

```bash
# .husky/pre-commit
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

pnpm lint-staged
pnpm type-check
pnpm test --run
```

### **Code Quality Tools**

#### **1. Biome Configuration**

```json
// biome.json
{
  "$schema": "https://biomejs.dev/schemas/1.4.1/schema.json",
  "organizeImports": {
    "enabled": true
  },
  "linter": {
    "enabled": true,
    "rules": {
      "recommended": true,
      "style": {
        "noNonNullAssertion": "error",
        "useConst": "error"
      },
      "suspicious": {
        "noExplicitAny": "warn"
      }
    }
  },
  "formatter": {
    "enabled": true,
    "indentStyle": "space",
    "indentWidth": 2,
    "lineWidth": 100
  },
  "javascript": {
    "formatter": {
      "quoteStyle": "single",
      "trailingComma": "es5",
      "semicolons": "asNeeded"
    }
  }
}
```

## 💰 Budget-Focused Features

*TripSage prioritizes budget-conscious travelers with comprehensive cost optimization tools, predictive pricing, and community-driven savings insights.*

### **Core Budget Feature Categories**

#### **1. Advanced Price Analysis & Prediction**

- **Real-time price monitoring** across multiple booking platforms
- **AI-powered price prediction** algorithms with confidence scoring
- **Historical price trends** and seasonal pattern analysis
- **Fare alert system** for target prices and routes
- **"Best time to book"** recommendations

#### **2. Total Cost Optimization**

- **Comprehensive expense calculator** covering all trip aspects
- **Hidden cost detection** (taxes, fees, tips, transport)
- **Alternative route analysis** (split ticketing, nearby airports)
- **Group travel cost optimization** with shared expense tracking
- **Currency conversion** with fee minimization strategies

#### **3. Smart Deal Discovery**

- **Error fare monitoring** and flash sale aggregation
- **Community deal sharing** platform with verification
- **Personalized deal alerts** based on travel preferences
- **Alternative destination suggestions** with cost comparisons
- **Seasonal opportunity identification**

### **Advanced Price Optimization**

#### **1. Flight Price Tracking**

```typescript
// components/features/budget/price-tracker.tsx
export const FlightPriceTracker = ({ route }: { route: FlightRoute }) => {
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([])
  const [prediction, setPrediction] = useState<PricePrediction | null>(null)
  
  useEffect(() => {
    const fetchPriceData = async () => {
      // Get historical prices
      const history = await priceApi.getHistoricalPrices(route)
      setPriceHistory(history)
      
      // Get price prediction
      const pred = await priceApi.getPricePrediction(route)
      setPrediction(pred)
    }
    
    fetchPriceData()
  }, [route])
  
  return (
    <Card>
      <CardHeader>
        <h3>Price Tracking</h3>
      </CardHeader>
      <CardContent>
        <PriceChart data={priceHistory} />
        
        {prediction && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-semibold">Price Prediction</h4>
            <p className="text-sm text-gray-600">
              {prediction.recommendation === 'buy' 
                ? `Best to book now. Prices expected to ${prediction.trend}.`
                : `Wait ${prediction.daysToWait} days. Prices may drop by ${prediction.expectedSavings}%.`
              }
            </p>
            <div className="mt-2">
              <span className="text-xs text-gray-500">
                Confidence: {prediction.confidence}%
              </span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

#### **2. Budget Optimization Engine**

```typescript
// lib/budget/optimization-engine.ts
export class BudgetOptimizationEngine {
  async optimizeTrip(trip: Trip, constraints: BudgetConstraints): Promise<OptimizationResult> {
    const optimizations = []
    
    // Flight optimizations
    const flightSavings = await this.optimizeFlights(trip.flights, constraints)
    optimizations.push(...flightSavings)
    
    // Accommodation optimizations
    const hotelSavings = await this.optimizeAccommodations(trip.accommodations, constraints)
    optimizations.push(...hotelSavings)
    
    // Activity optimizations
    const activitySavings = await this.optimizeActivities(trip.activities, constraints)
    optimizations.push(...activitySavings)
    
    return {
      totalSavings: optimizations.reduce((sum, opt) => sum + opt.savings, 0),
      optimizations: optimizations.sort((a, b) => b.savings - a.savings),
      alternativeTrip: await this.generateAlternativeTrip(trip, optimizations)
    }
  }
  
  private async optimizeFlights(flights: Flight[], constraints: BudgetConstraints) {
    const optimizations = []
    
    for (const flight of flights) {
      // Check alternative airports
      const altAirports = await this.findAlternativeAirports(flight.route)
      for (const airport of altAirports) {
        const altFlight = await this.searchAlternativeFlight(flight, airport)
        if (altFlight.price < flight.price) {
          optimizations.push({
            type: 'alternative_airport',
            original: flight,
            alternative: altFlight,
            savings: flight.price - altFlight.price,
            tradeoffs: [`${airport.distance}km from original destination`]
          })
        }
      }
      
      // Check split ticketing
      const splitOptions = await this.findSplitTicketOptions(flight.route)
      for (const split of splitOptions) {
        if (split.totalPrice < flight.price) {
          optimizations.push({
            type: 'split_ticket',
            original: flight,
            alternative: split,
            savings: flight.price - split.totalPrice,
            tradeoffs: ['Requires separate bookings', 'Longer total travel time']
          })
        }
      }
    }
    
    return optimizations
  }
}
```

#### **3. Smart Deal Detection**

```typescript
// components/features/budget/deal-detector.tsx
export const DealDetector = ({ searchParams }: { searchParams: SearchParams }) => {
  const [deals, setDeals] = useState<Deal[]>([])
  
  useEffect(() => {
    const detectDeals = async () => {
      const detectedDeals = await dealDetectionService.findDeals({
        ...searchParams,
        maxPrice: searchParams.budget,
        flexibleDates: true,
        includeAlternativeAirports: true
      })
      
      setDeals(detectedDeals)
    }
    
    detectDeals()
  }, [searchParams])
  
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">💰 Smart Deals Detected</h3>
      
      {deals.map(deal => (
        <Card key={deal.id} className="border-green-200 bg-green-50">
          <CardContent className="p-4">
            <div className="flex justify-between items-start">
              <div>
                <h4 className="font-semibold text-green-800">{deal.title}</h4>
                <p className="text-sm text-green-600">{deal.description}</p>
                <div className="mt-2 space-y-1">
                  {deal.features.map(feature => (
                    <span key={feature} className="inline-block bg-green-100 text-green-700 text-xs px-2 py-1 rounded mr-2">
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-green-700">
                  ${deal.price}
                </div>
                <div className="text-sm text-gray-500 line-through">
                  ${deal.originalPrice}
                </div>
                <div className="text-sm font-semibold text-green-600">
                  Save ${deal.savings} ({deal.savingsPercent}%)
                </div>
              </div>
            </div>
            
            <Button className="w-full mt-4 bg-green-600 hover:bg-green-700">
              Book This Deal
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

### **Budget Tracking Dashboard**

#### **Real-time Budget Monitoring**

```typescript
// components/features/budget/budget-dashboard.tsx
export const BudgetDashboard = ({ tripId }: { tripId: string }) => {
  const { budget, expenses, analytics } = useBudgetTracking(tripId)
  
  return (
    <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
      {/* Budget Overview */}
      <Card>
        <CardHeader>
          <h3>Total Budget</h3>
        </CardHeader>
        <CardContent>
          <div className="text-3xl font-bold">
            ${budget.total.toLocaleString()}
          </div>
          <Progress 
            value={(expenses.total / budget.total) * 100}
            className="mt-2"
          />
          <p className="text-sm text-gray-600 mt-1">
            ${(budget.total - expenses.total).toLocaleString()} remaining
          </p>
        </CardContent>
      </Card>
      
      {/* Category Breakdown */}
      {budget.categories.map(category => (
        <BudgetCategoryCard 
          key={category.name}
          category={category}
          spent={expenses.byCategory[category.name] || 0}
        />
      ))}
      
      {/* Spending Trends */}
      <Card className="md:col-span-2">
        <CardHeader>
          <h3>Spending Trends</h3>
        </CardHeader>
        <CardContent>
          <SpendingChart data={analytics.dailySpending} />
        </CardContent>
      </Card>
      
      {/* Savings Opportunities */}
      <Card className="lg:col-span-2">
        <CardHeader>
          <h3>💡 Savings Opportunities</h3>
        </CardHeader>
        <CardContent>
          <SavingsOpportunities 
            opportunities={analytics.savingsOpportunities}
          />
        </CardContent>
      </Card>
    </div>
  )
}
```

### **Comprehensive Trip Cost Calculator**

#### **Advanced Budget Interface**

```typescript
// components/features/budget/comprehensive-trip-calculator.tsx
interface TripCostBreakdown {
  flights: {
    base: number
    taxes: number
    baggage: number
    seatSelection: number
    meals: number
  }
  accommodation: {
    room: number
    taxes: number
    fees: number
    parkingTransport: number
  }
  transport: {
    airport: number
    local: number
    carRental: number
    fuel: number
  }
  activities: {
    tours: number
    attractions: number
    entertainment: number
  }
  dailyExpenses: {
    food: number
    drinks: number
    shopping: number
    misc: number
  }
  additionalCosts: {
    visa: number
    insurance: number
    vaccinations: number
    equipment: number
  }
}

export const ComprehensiveTripCalculator = ({ destination, dates }: CalculatorProps) => {
  const [costs, setCosts] = useState<TripCostBreakdown>(DEFAULT_COSTS)
  const [budgetTemplate, setBudgetTemplate] = useState<'backpacker' | 'midrange' | 'luxury'>('midrange')
  
  const totalCost = useMemo(() => {
    return Object.values(costs).reduce((total, category) => {
      return total + Object.values(category).reduce((sum, cost) => sum + cost, 0)
    }, 0)
  }, [costs])
  
  return (
    <div className="space-y-6">
      {/* Budget Template Selector */}
      <div className="flex gap-2">
        {['backpacker', 'midrange', 'luxury'].map(template => (
          <Button
            key={template}
            variant={budgetTemplate === template ? 'default' : 'outline'}
            onClick={() => setBudgetTemplate(template as any)}
            className="capitalize"
          >
            {template}
          </Button>
        ))}
      </div>
      
      {/* Cost Categories */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Object.entries(costs).map(([category, categoryData]) => (
          <Card key={category}>
            <CardHeader>
              <h4 className="capitalize font-semibold">{category.replace(/([A-Z])/g, ' $1')}</h4>
            </CardHeader>
            <CardContent>
              {Object.entries(categoryData).map(([item, cost]) => (
                <div key={item} className="flex justify-between items-center mb-2">
                  <span className="text-sm capitalize">{item.replace(/([A-Z])/g, ' $1')}</span>
                  <input
                    type="number"
                    value={cost}
                    onChange={(e) => updateCost(category, item, Number(e.target.value))}
                    className="w-20 text-right border rounded px-2 py-1"
                  />
                </div>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
      
      {/* Total Cost Summary */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-6">
          <div className="flex justify-between items-center">
            <div>
              <h3 className="text-2xl font-bold text-blue-800">
                Total Trip Cost: ${totalCost.toLocaleString()}
              </h3>
              <p className="text-blue-600">
                ${(totalCost / dates.length).toFixed(0)} per day
              </p>
            </div>
            <div className="text-right">
              <Button size="lg" className="bg-blue-600 hover:bg-blue-700">
                Save Budget Plan
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* Savings Recommendations */}
      <BudgetOptimizationSuggestions 
        costs={costs}
        destination={destination}
        dates={dates}
      />
    </div>
  )
}
```

### **Group Travel Cost Splitting**

#### **Shared Expense Management**

```typescript
// components/features/budget/group-cost-splitter.tsx
export const GroupCostSplitter = ({ tripId, participants }: GroupCostProps) => {
  const [expenses, setExpenses] = useState<SharedExpense[]>([])
  const [settlements, setSettlements] = useState<Settlement[]>([])
  
  const calculateSettlements = () => {
    const balances = new Map<string, number>()
    
    // Calculate each person's balance
    participants.forEach(person => {
      balances.set(person.id, 0)
    })
    
    expenses.forEach(expense => {
      const perPersonCost = expense.amount / expense.splitBetween.length
      
      // Payer gets credit
      balances.set(expense.paidBy, balances.get(expense.paidBy)! + expense.amount)
      
      // Split participants get debited
      expense.splitBetween.forEach(personId => {
        balances.set(personId, balances.get(personId)! - perPersonCost)
      })
    })
    
    // Generate optimal settlements
    const settlements = optimizeSettlements(balances)
    setSettlements(settlements)
  }
  
  return (
    <div className="space-y-6">
      {/* Quick Expense Entry */}
      <Card>
        <CardHeader>
          <h3>Add Shared Expense</h3>
        </CardHeader>
        <CardContent>
          <QuickExpenseForm 
            participants={participants}
            onAdd={(expense) => setExpenses([...expenses, expense])}
          />
        </CardContent>
      </Card>
      
      {/* Expense List */}
      <Card>
        <CardHeader>
          <h3>Trip Expenses</h3>
        </CardHeader>
        <CardContent>
          <ExpenseList 
            expenses={expenses}
            participants={participants}
            onEdit={updateExpense}
            onDelete={deleteExpense}
          />
        </CardContent>
      </Card>
      
      {/* Settlement Recommendations */}
      <Card>
        <CardHeader>
          <h3>💰 Settlement Plan</h3>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {settlements.map(settlement => (
              <div key={`${settlement.from}-${settlement.to}`} 
                   className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <span>
                  <strong>{settlement.fromName}</strong> owes <strong>{settlement.toName}</strong>
                </span>
                <span className="font-semibold text-green-600">
                  ${settlement.amount.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
          
          <Button 
            className="w-full mt-4" 
            onClick={() => sendSettlementNotifications(settlements)}
          >
            Send Settlement Requests
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
```

### **Currency & Fee Management**

#### **Smart Currency Tools**

```typescript
// components/features/budget/currency-manager.tsx
export const SmartCurrencyManager = ({ destination, budget }: CurrencyProps) => {
  const [exchangeRates, setExchangeRates] = useState<ExchangeRate[]>([])
  const [atmFees, setAtmFees] = useState<ATMFeeData>()
  const [recommendations, setRecommendations] = useState<CurrencyRecommendation[]>([])
  
  return (
    <div className="space-y-4">
      {/* Live Exchange Rates */}
      <Card>
        <CardHeader>
          <h3>💱 Live Exchange Rates</h3>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3">
            {exchangeRates.map(rate => (
              <div key={rate.currency} className="flex justify-between items-center">
                <span className="font-medium">{rate.currency}</span>
                <div className="text-right">
                  <div className="font-semibold">{rate.rate.toFixed(4)}</div>
                  <div className={`text-sm ${rate.trend === 'up' ? 'text-green-600' : 'text-red-600'}`}>
                    {rate.change24h > 0 ? '+' : ''}{rate.change24h.toFixed(2)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
      
      {/* ATM Fee Calculator */}
      <Card>
        <CardHeader>
          <h3>🏧 ATM Fee Analysis</h3>
        </CardHeader>
        <CardContent>
          <ATMFeeCalculator 
            destination={destination}
            withdrawalAmount={budget * 0.3} // Assume 30% cash needed
            userBank="chase" // From user profile
          />
        </CardContent>
      </Card>
      
      {/* Money Strategy Recommendations */}
      <Card>
        <CardHeader>
          <h3>💡 Money Strategy</h3>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recommendations.map((rec, index) => (
              <div key={index} className="p-3 bg-blue-50 rounded-lg">
                <h4 className="font-semibold text-blue-800">{rec.title}</h4>
                <p className="text-sm text-blue-600">{rec.description}</p>
                <div className="mt-2 text-xs text-blue-500">
                  Potential savings: ${rec.savingsEstimate}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
```

## 📝 Pydantic Usage Patterns

### **Model Development Standards**

TripSage extensively uses Pydantic v2 for data validation, API schemas, and configuration management. Here are the canonical patterns:

#### **1. Basic Model Definition**

```python
from typing import Annotated, Optional, Literal, List
from datetime import date, datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

class TravelRequest(BaseModel):
    """Model for validating travel request data."""
    
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        validate_default=True
    )
    
    destination: str = Field(..., min_length=2, description="Travel destination")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget: Annotated[float, Field(gt=0, description="Total budget in USD")]
    travelers: Annotated[int, Field(gt=0, le=20, description="Number of travelers")]
    
    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date, info: ValidationInfo) -> date:
        if hasattr(info.data, 'start_date') and v < info.data['start_date']:
            raise ValueError("End date must be after start date")
        return v
```

#### **2. API Request/Response Models**

```python
class FlightSearchRequest(BaseModel):
    """Request model for flight search API."""
    
    origin: str = Field(..., pattern=r'^[A-Z]{3}$', description="IATA airport code")
    destination: str = Field(..., pattern=r'^[A-Z]{3}$', description="IATA airport code")
    departure_date: date = Field(..., description="Departure date")
    return_date: Optional[date] = Field(None, description="Return date for round trip")
    passengers: int = Field(default=1, ge=1, le=9, description="Number of passengers")
    cabin_class: Literal["economy", "premium_economy", "business", "first"] = Field(default="economy")

class FlightSearchResponse(BaseModel):
    """Response model for flight search results."""
    
    search_id: str = Field(..., description="Unique search identifier")
    flights: List[FlightOffer] = Field(..., description="Available flight offers")
    total_results: int = Field(..., ge=0, description="Total number of results")
    search_duration_ms: int = Field(..., ge=0, description="Search duration in milliseconds")
```

---

*This comprehensive frontend development guide provides the foundation for building a modern, performant, and user-friendly travel planning interface with TripSage's advanced AI capabilities and extensive integration ecosystem.*
