# TripSage Frontend Quickstart Guide v2

This guide will help you get the TripSage frontend up and running quickly using the latest modern web technologies.

## Prerequisites

- Node.js 20+ and npm 10+
- Git
- Code editor (VS Code recommended)
- Vercel account (for deployment)
- API keys for:
  - OpenAI or Anthropic
  - Google Maps
  - OpenWeatherMap
  - Duffel (for flights)
  - Airbnb (optional)

## Quick Setup

### 1. Initialize the Project

```bash
# Create new Next.js 15 project
npx create-next-app@latest tripsage-frontend --typescript --app --tailwind

# Navigate to project
cd tripsage-frontend

# Open in VS Code
code .
```

### 2. Install Core Dependencies

```bash
# Core UI framework
npm install @radix-ui/themes class-variance-authority clsx tailwind-merge

# shadcn/ui setup
npx shadcn@latest init -d

# State management
npm install zustand immer

# Data fetching
npm install @tanstack/react-query

# AI SDK
npm install ai @ai-sdk/openai @ai-sdk/anthropic

# Forms and validation
npm install react-hook-form zod @hookform/resolvers

# Visualization
npm install recharts react-flow-renderer mapbox-gl
npm install --save-dev @types/mapbox-gl

# Animation
npm install framer-motion
```

### 3. Configure Tailwind CSS v4

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss'

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'oklch(var(--border))',
        input: 'oklch(var(--input))',
        ring: 'oklch(var(--ring))',
        background: 'oklch(var(--background))',
        foreground: 'oklch(var(--foreground))',
        primary: {
          DEFAULT: 'oklch(var(--primary))',
          foreground: 'oklch(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'oklch(var(--secondary))',
          foreground: 'oklch(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'oklch(var(--destructive))',
          foreground: 'oklch(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'oklch(var(--muted))',
          foreground: 'oklch(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'oklch(var(--accent))',
          foreground: 'oklch(var(--accent-foreground))',
        },
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}

export default config
```

### 4. Set Up Environment Variables

```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_OPENAI_KEY=
NEXT_PUBLIC_ANTHROPIC_KEY=
NEXT_PUBLIC_GOOGLE_MAPS_KEY=
NEXT_PUBLIC_WEATHER_API_KEY=
NEXT_PUBLIC_MAPBOX_TOKEN=
```

### 5. Create Base Layout

```tsx
// app/layout.tsx
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'TripSage - AI Travel Planning',
  description: 'Plan your perfect trip with AI assistance',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
```

### 6. Set Up Providers

```tsx
// components/providers.tsx
'use client'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { ThemeProvider } from 'next-themes'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        attribute="class"
        defaultTheme="dark"
        enableSystem
        disableTransitionOnChange
      >
        {children}
      </ThemeProvider>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  )
}
```

### 7. Create Your First Component

```tsx
// components/chat/ChatInterface.tsx
'use client'

import { useChat } from 'ai/react'

export function ChatInterface() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
  })

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto p-4">
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.map((message) => (
          <div
            key={message.id}
            className={`p-4 rounded-lg ${
              message.role === 'user'
                ? 'bg-primary text-primary-foreground ml-auto max-w-[80%]'
                : 'bg-muted max-w-[80%]'
            }`}
          >
            {message.content}
          </div>
        ))}
      </div>
      
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask about your travel plans..."
          className="flex-1 px-4 py-2 rounded-lg border bg-background"
          disabled={isLoading}
        />
        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </div>
  )
}
```

### 8. Add API Route for Chat

```typescript
// app/api/chat/route.ts
import { streamText } from 'ai'
import { openai } from '@ai-sdk/openai'

export const runtime = 'edge'

export async function POST(req: Request) {
  const { messages } = await req.json()

  const result = streamText({
    model: openai('gpt-4-turbo'),
    messages,
    temperature: 0.7,
    maxTokens: 4000,
  })

  return result.toDataStreamResponse()
}
```

### 9. Run the Development Server

```bash
# Start development server
npm run dev

# Open in browser
open http://localhost:3000
```

## Advanced Setup

### Add Zustand Store

```typescript
// stores/chatStore.ts
import { create } from 'zustand'
import { immer } from 'zustand/middleware/immer'

interface ChatStore {
  messages: Message[]
  activeAgents: Agent[]
  isStreaming: boolean
  addMessage: (message: Message) => void
  setActiveAgents: (agents: Agent[]) => void
}

export const useChatStore = create<ChatStore>()(
  immer((set) => ({
    messages: [],
    activeAgents: [],
    isStreaming: false,
    
    addMessage: (message) =>
      set((state) => {
        state.messages.push(message)
      }),
      
    setActiveAgents: (agents) =>
      set((state) => {
        state.activeAgents = agents
      }),
  }))
)
```

### Add Agent Visualization

```tsx
// components/agents/AgentStatus.tsx
import { motion } from 'framer-motion'

export function AgentStatus({ agent }: { agent: Agent }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2 p-2 bg-card rounded-lg"
    >
      <div className={`w-2 h-2 rounded-full ${
        agent.status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
      }`} />
      <span className="text-sm font-medium">{agent.name}</span>
      {agent.task && (
        <span className="text-xs text-muted-foreground">{agent.task}</span>
      )}
    </motion.div>
  )
}
```

### Add Map Integration

```tsx
// components/map/TripMap.tsx
import mapboxgl from 'mapbox-gl'
import { useEffect, useRef } from 'react'

mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN!

export function TripMap({ locations }: { locations: Location[] }) {
  const mapContainer = useRef<HTMLDivElement>(null)
  const map = useRef<mapboxgl.Map | null>(null)

  useEffect(() => {
    if (!mapContainer.current) return

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/dark-v11',
      center: [-74.5, 40],
      zoom: 9,
    })

    // Add markers for locations
    locations.forEach((location) => {
      new mapboxgl.Marker()
        .setLngLat([location.lng, location.lat])
        .addTo(map.current!)
    })

    return () => map.current?.remove()
  }, [locations])

  return <div ref={mapContainer} className="h-[400px] rounded-lg" />
}
```

## Testing

### Unit Tests

```typescript
// __tests__/components/ChatInterface.test.tsx
import { render, screen } from '@testing-library/react'
import { ChatInterface } from '@/components/chat/ChatInterface'

describe('ChatInterface', () => {
  it('renders input and button', () => {
    render(<ChatInterface />)
    
    expect(screen.getByPlaceholderText(/ask about your travel plans/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /send/i })).toBeInTheDocument()
  })
})
```

### E2E Tests

```typescript
// e2e/chat.spec.ts
import { test, expect } from '@playwright/test'

test('can send a chat message', async ({ page }) => {
  await page.goto('/')
  
  const input = page.getByPlaceholderText(/ask about your travel plans/i)
  const button = page.getByRole('button', { name: /send/i })
  
  await input.fill('Plan a trip to Paris')
  await button.click()
  
  await expect(page.getByText(/paris/i)).toBeVisible()
})
```

## Deployment

### Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel

# Follow prompts to configure project
```

### Environment Variables

Set these in Vercel dashboard:
- `NEXT_PUBLIC_API_URL`
- All API keys from `.env.local`

## Common Issues

### 1. Hydration Errors
- Ensure all client components have `'use client'` directive
- Use `suppressHydrationWarning` for theme switching elements

### 2. Type Errors
- Run `npm run type-check` to catch TypeScript errors
- Use proper type imports from packages

### 3. Build Errors
- Clear `.next` folder: `rm -rf .next`
- Clear node_modules: `rm -rf node_modules && npm install`

## Next Steps

1. Implement authentication with Clerk or Auth.js
2. Add more UI components from shadcn/ui
3. Integrate with backend MCP servers
4. Add real-time features with WebSockets
5. Implement PWA capabilities
6. Add internationalization with next-intl

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [React Documentation](https://react.dev)
- [Tailwind CSS Documentation](https://tailwindcss.com/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [Vercel AI SDK](https://sdk.vercel.ai/docs)
- [Zustand Documentation](https://github.com/pmndrs/zustand)
- [React Query Documentation](https://tanstack.com/query/latest)

## Support

- GitHub Issues: [github.com/tripsage/frontend/issues](https://github.com/tripsage/frontend/issues)
- Discord: [discord.gg/tripsage](https://discord.gg/tripsage)
- Documentation: [docs.tripsage.ai](https://docs.tripsage.ai)