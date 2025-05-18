# TripSage Frontend Architecture

## Executive Summary

TripSage's frontend is a modern, AI-centric travel planning application built with Next.js 15.3, React 19, and TypeScript 5.5. It provides real-time streaming interfaces for agent interactions using Vercel AI SDK v5, integrates seamlessly with the FastAPI backend and MCP servers, and is optimized for deployment on Vercel with edge runtime capabilities.

## Technology Stack

### Core Framework

- **Next.js 15.3**: App Router, Server Components, Turbopack (production builds)
- **React 19**: Concurrent features, new hooks (use, useOptimistic), automatic batching
- **TypeScript 5.5+**: Enhanced type inference, type predicates, improved performance

### Styling & UI

- **Tailwind CSS v4**: OKLCH color space, container queries, enhanced theming
- **shadcn/ui v3-canary**: React 19 compatibility, accessible components built on Radix UI
- **Framer Motion v11**: Advanced animations and gestures
- **lucide-react**: Modern icon library

### State Management

- **Zustand v5**: Client state management with TypeScript-first API
- **TanStack Query v5**: Server state, caching, optimistic updates
- **React Hook Form v8**: Form handling with Next.js 15 compatibility
- **Zod v3**: Runtime validation with TypeScript inference

### Real-time & AI

- **Vercel AI SDK v5**: UI Message Streaming Protocol, agent interactions
- **Server-Sent Events (SSE)**: Primary streaming mechanism for AI responses
- **WebSocket (fallback)**: Bidirectional communication when needed

### Authentication

- **Supabase Auth**: Integrated with backend, JWT-based
- **iron-session**: Secure session management for server components
- **Custom middleware**: Protected routes and API endpoints

### Maps & Visualization

- **Mapbox GL JS v3**: Interactive maps with WebGL performance
- **React Flow v12**: Agent workflow visualization
- **Recharts v2**: Data visualization for analytics

### Development & Build

- **Turbopack**: Next.js integrated bundler (28-83% faster builds)
- **Vitest v2**: Unit testing with native ESM support
- **Playwright v1.48+**: E2E testing with Next.js 15 support
- **Biome**: Fast linting and formatting (ruff equivalent for JS/TS)

## Directory Structure

```
src/
├── app/                      # Next.js 15 App Router
│   ├── (auth)/              # Authentication route group
│   │   ├── login/
│   │   ├── register/
│   │   └── reset-password/
│   ├── (dashboard)/         # Protected dashboard routes
│   │   ├── layout.tsx       # Shared dashboard layout
│   │   ├── page.tsx         # Dashboard home
│   │   ├── trips/           # Trip management
│   │   ├── agents/          # Agent chat interfaces
│   │   └── settings/        # User settings
│   ├── api/                 # API routes
│   │   ├── agents/          # Agent streaming endpoints
│   │   │   └── [agentId]/   
│   │   │       └── stream/
│   │   ├── auth/            # Auth endpoints
│   │   └── trpc/            # Optional tRPC router
│   ├── layout.tsx          # Root layout with providers
│   ├── error.tsx           # Error boundary
│   └── global-error.tsx    # Global error handler
│
├── components/              # React components
│   ├── ui/                 # Base UI components (shadcn/ui)
│   │   ├── button.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   ├── agents/             # Agent-specific components
│   │   ├── agent-chat.tsx
│   │   ├── message-list.tsx
│   │   ├── tool-invocation.tsx
│   │   └── workflow-visualizer.tsx
│   ├── trips/              # Trip planning components
│   │   ├── trip-card.tsx
│   │   ├── itinerary-builder.tsx
│   │   └── budget-tracker.tsx
│   ├── auth/               # Authentication components
│   │   ├── login-form.tsx
│   │   └── auth-provider.tsx
│   └── shared/             # Shared components
│       ├── header.tsx
│       ├── sidebar.tsx
│       └── loading.tsx
│
├── hooks/                  # Custom React hooks
│   ├── use-agent-stream.ts
│   ├── use-auth.ts
│   ├── use-mcp-tool.ts
│   └── use-realtime.ts
│
├── lib/                    # Core utilities
│   ├── api/               # API client configuration
│   │   ├── client.ts      # Configured fetch client
│   │   └── endpoints.ts   # API endpoint constants
│   ├── ai/                # AI SDK configuration
│   │   ├── stream.ts      # Streaming utilities
│   │   └── agents.ts      # Agent configurations
│   ├── supabase/          # Supabase client setup
│   │   ├── client.ts
│   │   └── server.ts      # Server-side client
│   └── utils/             # General utilities
│       ├── cn.ts          # clsx + tailwind merge
│       └── format.ts      # Formatting helpers
│
├── services/              # Business logic services
│   ├── agent-service.ts   # Agent communication
│   ├── trip-service.ts    # Trip management
│   └── auth-service.ts    # Authentication logic
│
├── stores/                # Zustand stores
│   ├── auth-store.ts
│   ├── agent-store.ts
│   ├── trip-store.ts
│   └── ui-store.ts
│
├── types/                 # TypeScript definitions
│   ├── api.ts             # API response types
│   ├── agent.ts           # Agent-related types
│   ├── trip.ts            # Trip domain types
│   └── mcp.ts             # MCP tool types
│
└── styles/               # Global styles
    ├── globals.css       # Global CSS with Tailwind
    └── themes.css        # OKLCH theme variables
```

## Core Architecture Layers

### 1. Presentation Layer

- **Server Components**: Default for static content, SEO-optimized pages
- **Client Components**: Interactive features, real-time updates
- **Streaming UI**: Token-by-token rendering for AI responses
- **Mobile-First Design**: Responsive layouts with Tailwind container queries

### 2. State Management Layer

```typescript
// Client State (Zustand)
interface UIStore {
  theme: 'light' | 'dark' | 'system'
  sidebarOpen: boolean
  activeAgent: string | null
}

// Server State (TanStack Query)
const useTrips = () => {
  return useQuery({
    queryKey: ['trips'],
    queryFn: () => api.get('/trips'),
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// Real-time State (Vercel AI SDK)
const { messages, input, handleSubmit } = useChat({
  api: '/api/agents/travel-planner/stream',
  streamProtocol: 'data-stream',
})
```

### 3. API Integration Layer

```typescript
// API Client with automatic retry and error handling
class TripSageAPI {
  private baseURL = process.env.NEXT_PUBLIC_API_URL
  
  async request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseURL}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${await getSessionToken()}`,
        ...options?.headers,
      },
    })
    
    if (!res.ok) {
      throw new APIError(res.status, await res.text())
    }
    
    return res.json()
  }
}
```

### 4. Real-time Communication Layer

```typescript
// Agent streaming with SSE
export async function POST(req: Request) {
  const encoder = new TextEncoder()
  
  const stream = new ReadableStream({
    async start(controller) {
      const { messages } = await req.json()
      
      // Call FastAPI backend
      const response = await fetch(`${BACKEND_URL}/agents/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ messages }),
      })
      
      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      
      while (true) {
        const { done, value } = await reader!.read()
        if (done) break
        
        const chunk = decoder.decode(value)
        controller.enqueue(encoder.encode(chunk))
      }
      
      controller.close()
    },
  })
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  })
}
```

## Component Strategy

### Server Components (Default)

```typescript
// app/(dashboard)/trips/page.tsx
export default async function TripsPage() {
  const trips = await api.get('/trips')
  
  return (
    <div className="container py-8">
      <TripGrid trips={trips} />
    </div>
  )
}
```

### Client Components

```typescript
'use client'

// components/agents/agent-chat.tsx
export function AgentChat({ agentId }: { agentId: string }) {
  const { messages, input, handleSubmit, isLoading } = useChat({
    api: `/api/agents/${agentId}/stream`,
    streamProtocol: 'data-stream',
  })
  
  return (
    <div className="flex flex-col h-full">
      <MessageList messages={messages} />
      <ChatInput
        value={input}
        onChange={handleInputChange}
        onSubmit={handleSubmit}
        disabled={isLoading}
      />
    </div>
  )
}
```

### Streaming Components

```typescript
// components/agents/streaming-message.tsx
export function StreamingMessage({ content }: { content: string }) {
  const [displayedContent, setDisplayedContent] = useState('')
  
  useEffect(() => {
    let index = 0
    const interval = setInterval(() => {
      if (index < content.length) {
        setDisplayedContent(content.slice(0, index + 1))
        index++
      } else {
        clearInterval(interval)
      }
    }, 10) // Smooth character-by-character display
    
    return () => clearInterval(interval)
  }, [content])
  
  return <div className="prose">{displayedContent}</div>
}
```

## Authentication Strategy

### Supabase Auth Integration

```typescript
// lib/supabase/server.ts
import { createServerClient } from '@supabase/ssr'
import { cookies } from 'next/headers'

export function createClient() {
  const cookieStore = cookies()
  
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) =>
            cookieStore.set(name, value, options)
          )
        },
      },
    }
  )
}
```

### Middleware Protection

```typescript
// middleware.ts
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export async function middleware(request: NextRequest) {
  const supabase = createClient()
  const { data: { user } } = await supabase.auth.getUser()
  
  if (!user && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  
  return NextResponse.next()
}

export const config = {
  matcher: ['/dashboard/:path*', '/api/protected/:path*'],
}
```

## MCP Server Interaction Pattern

### Backend-Only MCP Communication

All interactions with MCP servers are exclusively handled through the FastAPI backend. The frontend never makes direct calls to MCP servers.

**Architecture:**

```
Frontend (Next.js) → FastAPI Backend → MCPManager → MCP Servers
```

**Benefits:**

- API keys remain server-side only
- Centralized error handling and retry logic
- Consistent monitoring and logging
- Flexible MCP implementation changes without frontend impact

### Example Flow

```typescript
// Frontend makes authenticated request to backend
const response = await api.post('/agents/travel-planner/search', {
  destination: 'Paris',
  dates: { start: '2025-06-01', end: '2025-06-07' }
});

// Backend handles MCP orchestration
// 1. Retrieves user's decrypted API keys
// 2. Invokes appropriate MCP wrappers
// 3. Aggregates and normalizes responses
// 4. Returns unified result to frontend
```

## Secure API Key Management (BYOK)

### Architecture Overview

TripSage implements a secure Bring Your Own Key (BYOK) system allowing users to provide their own API keys for external services.

### Key Components

#### 1. Frontend Key Input

```typescript
// components/settings/api-key-manager.tsx
interface ApiKeyFormData {
  service: 'openai' | 'duffel' | 'mapbox' | 'weatherapi';
  apiKey: string;
}

export function ApiKeyManager() {
  const [showKey, setShowKey] = useState(false);
  
  const handleSubmit = async (data: ApiKeyFormData) => {
    // Always use HTTPS in production
    const response = await fetch('/api/user/keys', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${sessionToken}`,
      },
      body: JSON.stringify({
        service: data.service,
        api_key: data.apiKey,
      }),
    });
    
    // Clear the key from memory immediately after submission
    data.apiKey = '';
  };
  
  return (
    <Form onSubmit={handleSubmit}>
      <Select name="service" label="Service">
        <option value="openai">OpenAI</option>
        <option value="duffel">Duffel Flights</option>
        <option value="mapbox">Mapbox</option>
        <option value="weatherapi">Weather API</option>
      </Select>
      
      <Input
        name="apiKey"
        type={showKey ? 'text' : 'password'}
        label="API Key"
        autoComplete="off"
        spellCheck={false}
      />
      
      <Button type="submit">Save API Key</Button>
    </Form>
  );
}
```

#### 2. Secure Transmission

- HTTPS-only communication
- JWT-authenticated endpoints
- Keys transmitted once and never stored client-side

#### 3. Backend Encryption & Storage

```python
# Backend handles secure storage (Python/FastAPI)
# Fernet symmetric encryption
encrypted_key = cipher.encrypt(api_key.encode())

# Stored in Supabase
user_api_keys: {
  user_id: string
  service: string
  encrypted_key: string (base64)
  key_hash: string (SHA256 prefix for identification)
  created_at: timestamp
  updated_at: timestamp
}
```

#### 4. Key Usage Flow

1. Agent/service requests key for specific service
2. KeyManager retrieves encrypted key from database
3. Key decrypted in memory with short TTL cache (5 min)
4. Key used for MCP invocation
5. Key cleared from memory after use

#### 5. Frontend Status Display

```typescript
// components/settings/api-key-status.tsx
interface ApiKeyStatus {
  service: string;
  isSet: boolean;
  lastUpdated?: string;
  keyPreview?: string; // First 4 and last 4 characters only
}

export function ApiKeyStatusList() {
  const [statuses, setStatuses] = useState<ApiKeyStatus[]>([]);
  
  useEffect(() => {
    // Fetch key statuses (never the actual keys)
    fetch('/api/user/keys/status', {
      headers: {
        'Authorization': `Bearer ${sessionToken}`,
      },
    })
      .then(res => res.json())
      .then(data => setStatuses(data));
  }, []);
  
  return (
    <div className="space-y-4">
      {statuses.map(status => (
        <div key={status.service} className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">{status.service}</h3>
            <p className="text-sm text-gray-500">
              {status.isSet ? (
                <>
                  Key set • Preview: {status.keyPreview} • 
                  Last updated: {formatDate(status.lastUpdated)}
                </>
              ) : (
                'No key configured'
              )}
            </p>
          </div>
          <Button
            onClick={() => openKeyModal(status.service)}
            variant={status.isSet ? 'secondary' : 'primary'}
          >
            {status.isSet ? 'Update' : 'Add'} Key
          </Button>
        </div>
      ))}
    </div>
  );
}
```

### Security Measures

- Master encryption key managed by secure key service (AWS KMS, Azure Key Vault)
- Keys encrypted at rest using Fernet (AES-128 CBC + HMAC)
- Short-lived memory cache for performance
- Audit logging for all key operations
- Key rotation support
- Secure key deletion with crypto-shredding

## Agent-Specific Components

### Flight Agent Components

```typescript
// components/agents/flight/flight-results.tsx
export function FlightResults({ offers }: { offers: DuffelOffer[] }) {
  return (
    <div className="space-y-4">
      {offers.map(offer => (
        <FlightOfferCard
          key={offer.id}
          offer={offer}
          segments={offer.segments}
          pricing={offer.pricing}
        />
      ))}
    </div>
  )
}

// components/agents/flight/segment-display.tsx
export function SegmentDisplay({ segment }: { segment: FlightSegment }) {
  return (
    <div className="flex items-center gap-4">
      <AirlineInfo carrier={segment.airline} />
      <FlightTimes departure={segment.departure} arrival={segment.arrival} />
      <DurationBadge duration={segment.duration} />
    </div>
  )
}
```

### Accommodation Agent Components

```typescript
// components/agents/accommodation/listing-grid.tsx
export function AccommodationGrid({ listings }: { listings: AirbnbListing[] }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {listings.map(listing => (
        <ListingCard
          key={listing.id}
          listing={listing}
          amenities={listing.amenities}
          pricing={listing.pricing}
        />
      ))}
    </div>
  )
}
```

### Destination Research Components

```typescript
// components/agents/research/content-display.tsx
export function ResearchContent({ content }: { content: WebCrawlResult }) {
  return (
    <div className="prose max-w-none">
      <CrawlSourceBadge source={content.source} domain={content.domain} />
      <div dangerouslySetInnerHTML={{ __html: content.sanitizedHtml }} />
      <ExtractedDataSummary data={content.extractedData} />
    </div>
  )
}
```

### MCP Tool Result Components

```typescript
// components/mcp/weather-widget.tsx
export function WeatherWidget({ forecast }: { forecast: WeatherForecast }) {
  return (
    <div className="weather-card">
      <CurrentConditions data={forecast.current} />
      <DailyForecast days={forecast.daily} />
      <WeatherAlerts alerts={forecast.alerts} />
    </div>
  )
}

// components/mcp/map-display.tsx
export function MCPMapDisplay({ places }: { places: GooglePlacesResult[] }) {
  return (
    <MapContainer>
      {places.map(place => (
        <PlaceMarker
          key={place.id}
          place={place}
          onClick={() => showPlaceDetails(place)}
        />
      ))}
    </MapContainer>
  )
}
```

## Web Crawling Integration

### Crawl Control Interface

```typescript
// components/webcrawl/crawl-control.tsx
export function CrawlControl({ onCrawl }: { onCrawl: (url: string) => void }) {
  const [crawlStatus, setCrawlStatus] = useState<CrawlStatus>()

  return (
    <div className="crawl-interface">
      <CrawlUrlInput onSubmit={onCrawl} />
      <DomainRoutingIndicator domain={crawlStatus?.domain} />
      <CrawlProgress status={crawlStatus} />
      <CrawlResults results={crawlStatus?.results} />
    </div>
  )
}

// services/crawl-service.ts
export class CrawlService {
  async initiateHybridCrawl(url: string): Promise<CrawlResult> {
    // Calls backend which handles domain-based routing
    const response = await api.post('/api/crawl/hybrid', { url })
    return response.data
  }

  subscribeToCrawlUpdates(crawlId: string): EventSource {
    return new EventSource(`/api/crawl/${crawlId}/stream`)
  }
}
```

### Crawl Result Display

```typescript
// components/webcrawl/result-viewer.tsx
export function CrawlResultViewer({ result }: { result: CrawlResult }) {
  const getSourceIcon = (source: string) => {
    switch(source) {
      case 'crawl4ai': return <Crawl4AIIcon />
      case 'firecrawl': return <FirecrawlIcon />
      case 'playwright': return <PlaywrightIcon />
    }
  }

  return (
    <div className="crawl-result">
      <header className="flex items-center gap-2">
        {getSourceIcon(result.source)}
        <span>{result.domain}</span>
        <CrawlTimestamp time={result.timestamp} />
      </header>
      <ContentDisplay content={result.content} type={result.contentType} />
    </div>
  )
}
```

## Tool Invocation Visualization

### Tool Invocation Tracking

```typescript
// components/agents/tool-tracker.tsx
export function ToolInvocationTracker({ agentId }: { agentId: string }) {
  const { invocations } = useToolInvocations(agentId)

  return (
    <div className="tool-tracker">
      {invocations.map(inv => (
        <ToolInvocationCard
          key={inv.id}
          tool={inv.tool}
          status={inv.status}
          input={inv.input}
          output={inv.output}
          duration={inv.duration}
        />
      ))}
    </div>
  )
}

// types/agent.ts
interface ToolInvocation {
  id: string
  tool: MCPTool
  status: 'pending' | 'running' | 'success' | 'error'
  input: Record<string, any>
  output?: Record<string, any>
  error?: string
  duration?: number
  timestamp: Date
}
```

## Error Handling Strategy

### Global Error Boundary

```typescript
// app/error.tsx
'use client'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    // Log error to monitoring service
    console.error(error)
  }, [error])
  
  return (
    <div className="flex h-full flex-col items-center justify-center">
      <h2 className="text-2xl font-semibold">Something went wrong!</h2>
      <button
        onClick={reset}
        className="mt-4 rounded-md bg-blue-500 px-4 py-2 text-white"
      >
        Try again
      </button>
    </div>
  )
}
```

### API Error Handling

```typescript
// lib/api/errors.ts
export class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

// With TanStack Query
function useTrips() {
  return useQuery({
    queryKey: ['trips'],
    queryFn: fetchTrips,
    retry: (failureCount, error) => {
      if (error instanceof APIError && error.status === 401) {
        return false // Don't retry auth errors
      }
      return failureCount < 3
    },
    onError: (error) => {
      toast.error(error.message)
    },
  })
}
```

## Performance Optimization

### Code Splitting & Lazy Loading

```typescript
// Dynamic imports for heavy components
const MapView = dynamic(() => import('@/components/maps/map-view'), {
  loading: () => <div>Loading map...</div>,
  ssr: false,
})

const WorkflowVisualizer = dynamic(
  () => import('@/components/agents/workflow-visualizer'),
  { loading: () => <Skeleton className="h-96" /> }
)
```

### Image Optimization

```typescript
import Image from 'next/image'

export function DestinationCard({ destination }) {
  return (
    <div className="relative aspect-video">
      <Image
        src={destination.image}
        alt={destination.name}
        fill
        sizes="(max-width: 768px) 100vw, (max-width: 1200px) 50vw, 33vw"
        className="object-cover"
        priority={destination.featured}
      />
    </div>
  )
}
```

### Streaming Optimization

```typescript
// Throttled updates for rapid token streams
const { messages } = useChat({
  api: '/api/agents/chat',
  streamProtocol: 'data-stream',
  experimental_throttle: 50, // Update UI every 50ms max
})
```

## Testing Strategy

### Unit Tests (Vitest)

```typescript
// components/ui/button.test.tsx
import { render, screen } from '@testing-library/react'
import { Button } from './button'

describe('Button', () => {
  it('renders with correct text', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button')).toHaveTextContent('Click me')
  })
  
  it('handles click events', async () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    await userEvent.click(screen.getByRole('button'))
    expect(handleClick).toHaveBeenCalledOnce()
  })
})
```

### Integration Tests

```typescript
// app/api/agents/[agentId]/stream/route.test.ts
describe('Agent Streaming API', () => {
  it('returns SSE stream for valid requests', async () => {
    const response = await fetch('/api/agents/travel-planner/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: [{ role: 'user', content: 'Plan a trip to Paris' }] }),
    })
    
    expect(response.headers.get('content-type')).toBe('text/event-stream')
    expect(response.ok).toBe(true)
  })
})
```

### E2E Tests (Playwright)

```typescript
// e2e/trip-planning.spec.ts
test('complete trip planning flow', async ({ page }) => {
  await page.goto('/dashboard')
  await page.click('text=Plan New Trip')
  
  await page.fill('[name="destination"]', 'Paris, France')
  await page.fill('[name="startDate"]', '2025-06-01')
  await page.fill('[name="endDate"]', '2025-06-07')
  
  await page.click('text=Start Planning')
  
  // Wait for agent response
  await expect(page.locator('.agent-message')).toContainText('I can help you plan')
})
```

## Deployment Configuration

### Vercel Deployment

```json
// vercel.json
{
  "functions": {
    "app/api/agents/*/stream/route.ts": {
      "maxDuration": 30
    }
  },
  "env": {
    "NEXT_PUBLIC_API_URL": "@production-api-url",
    "NEXT_PUBLIC_SUPABASE_URL": "@supabase-url",
    "NEXT_PUBLIC_SUPABASE_ANON_KEY": "@supabase-anon-key"
  }
}
```

### Environment Variables

```env
# .env.local
NEXT_PUBLIC_API_URL=https://api.tripsage.ai
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-key
MAPBOX_ACCESS_TOKEN=your-mapbox-token
```

## Security Considerations

### Content Security Policy

```typescript
// next.config.mjs
const securityHeaders = [
  {
    key: 'Content-Security-Policy',
    value: `
      default-src 'self';
      script-src 'self' 'unsafe-eval' 'unsafe-inline' https://vercel.live;
      style-src 'self' 'unsafe-inline';
      img-src 'self' data: https:;
      connect-src 'self' https://*.supabase.co wss://*.supabase.co https://api.mapbox.com;
    `.replace(/\n/g, ' ')
  },
  {
    key: 'X-Frame-Options',
    value: 'DENY'
  },
  {
    key: 'X-Content-Type-Options',
    value: 'nosniff'
  }
]
```

### API Security

- All sensitive operations proxied through backend
- JWT tokens validated on every request
- Rate limiting on API endpoints
- Input validation with Zod schemas

## Monitoring & Analytics

### Performance Monitoring

```typescript
// lib/monitoring.ts
export function reportWebVitals(metric: NextWebVitalsMetric) {
  if (metric.label === 'web-vital') {
    // Send to analytics service
    analytics.track('Web Vitals', {
      metric: metric.name,
      value: metric.value,
      label: metric.label,
    })
  }
}
```

### Error Tracking

```typescript
// lib/sentry.ts
import * as Sentry from '@sentry/nextjs'

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  tracesSampleRate: 1.0,
  debug: false,
  environment: process.env.NODE_ENV,
})
```

## Future Enhancements

### Progressive Web App

- Service Worker implementation
- Offline functionality
- Push notifications

### Advanced AI Features

- Voice input/output
- Multi-modal agent interactions
- Predictive UI based on user behavior

### Performance Improvements

- Edge runtime for API routes
- Partial pre-rendering
- React Server Components optimization

This architecture provides a solid foundation for TripSage's frontend, ensuring scalability, performance, and an excellent developer experience while maintaining flexibility for future enhancements.
