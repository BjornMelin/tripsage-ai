# Vercel AI SDK v5 Integration Guide for TripSage

This guide covers the integration of Vercel AI SDK v5 with Next.js 15 App Router, featuring the new UI Message Streaming Protocol, OpenTelemetry support, and advanced streaming capabilities.

## Overview

Vercel AI SDK v5 introduces significant improvements:
- **UI Message Streaming Protocol**: Structured streaming with typed JSON objects
- **Enhanced Telemetry**: OpenTelemetry integration for tracing
- **Improved Developer Experience**: Better TypeScript support and error handling
- **Flexible Streaming**: Support for text, reasoning, tool calls, files, and metadata

## Setup

### 1. Install Dependencies

```bash
pnpm add ai @ai-sdk/openai @ai-sdk/anthropic zod @vercel/otel
```

### 2. Environment Variables

```env
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
PERPLEXITY_API_KEY=your_perplexity_key  # Optional
```

### 3. OpenTelemetry Configuration

Create `instrumentation.ts` in your project root:

```typescript
import { registerOTel } from '@vercel/otel'

export function register() {
  registerOTel({
    serviceName: 'tripsage-frontend',
    instrumentations: [], // SDK auto-instruments
  })
}
```

## UI Message Streaming Protocol

The new protocol provides structured streaming with typed JSON objects:

### Message Stream Parts

```typescript
// Type definitions for UI Message Stream
interface UIMessageStreamPart {
  type: 'start' | 'finish' | 'error' | 'text' | 'reasoning' | 'tool-call' | 'file' | 'metadata'
  [key: string]: any
}

interface StartPart {
  type: 'start'
  messageId: string
  timestamp: Date
}

interface TextPart {
  type: 'text'
  delta: string
}

interface ToolCallPart {
  type: 'tool-call'
  toolCallId: string
  toolName: string
  args: any
}
```

## Chat Interface Implementation

### Route Handler with Streaming (`app/api/chat/route.ts`)

```typescript
import { streamText } from 'ai'
import { openai } from '@ai-sdk/openai'
import { z } from 'zod'

// Tool definitions with Zod schemas
const tools = {
  searchFlights: {
    description: 'Search for flights between destinations',
    parameters: z.object({
      origin: z.string().length(3).describe('Airport code'),
      destination: z.string().length(3).describe('Airport code'),
      departureDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      returnDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
      passengers: z.number().min(1).max(9).default(1),
    }),
    execute: async (args) => {
      // Execute flight search
      return await searchFlightsAPI(args)
    },
  },
  searchAccommodations: {
    description: 'Search for accommodations',
    parameters: z.object({
      location: z.string(),
      checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      guests: z.number().min(1).max(10),
    }),
    execute: async (args) => {
      // Execute accommodation search
      return await searchAccommodationsAPI(args)
    },
  },
}

export async function POST(req: Request) {
  const { messages } = await req.json()

  // Stream text with tools and telemetry
  const result = streamText({
    model: openai('gpt-4-turbo'),
    messages,
    tools,
    toolCallStreaming: true, // Enable tool call streaming
    experimental_telemetry: {
      isEnabled: true,
      metadata: {
        userId: req.headers.get('x-user-id'),
        sessionId: req.headers.get('x-session-id'),
      },
    },
  })

  // Convert to UI Message Stream Response
  return result.toUIMessageStreamResponse({
    headers: {
      'x-vercel-ai-ui-message-stream': 'v1',
    },
  })
}
```

### Client-Side Hook with Streaming

```typescript
// app/(dashboard)/chat/page.tsx
'use client'

import { useChat } from 'ai/react'
import { useUIMessageStream } from '@/hooks/useUIMessageStream'

export default function ChatPage() {
  const { 
    messages, 
    input, 
    handleInputChange, 
    handleSubmit,
    isLoading,
    error,
  } = useChat({
    api: '/api/chat',
    streamProtocol: 'ui', // Use UI Message Stream Protocol
    experimental_throttle: 50, // Throttle UI updates (ms)
    onFinish: (message) => {
      console.log('Message completed:', message)
    },
    onError: (error) => {
      console.error('Chat error:', error)
    },
  })

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((message) => (
          <div key={message.id} className="mb-4">
            <div className="font-semibold">
              {message.role === 'user' ? 'You' : 'AI'}
            </div>
            <div className="mt-1">
              {message.content}
              {message.toolInvocations?.map((toolInvocation) => (
                <ToolInvocationDisplay
                  key={toolInvocation.toolCallId}
                  toolInvocation={toolInvocation}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
      
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <input
          className="w-full p-2 border rounded"
          value={input}
          onChange={handleInputChange}
          placeholder="Ask about your travel plans..."
          disabled={isLoading}
        />
      </form>
    </div>
  )
}
```

### Manual Stream Processing

For advanced use cases, manually process the UI Message Stream:

```typescript
// lib/stream-processor.ts
import { processUIMessageStream } from 'ai'

export async function processCustomStream(stream: ReadableStream) {
  const { messages } = await processUIMessageStream({
    stream,
    onStart: ({ messageId }) => {
      console.log('Stream started:', messageId)
    },
    onText: ({ delta }) => {
      console.log('Text delta:', delta)
    },
    onToolCall: ({ toolName, args }) => {
      console.log('Tool call:', toolName, args)
    },
    onFinish: ({ finishReason, usage }) => {
      console.log('Finished:', finishReason, usage)
    },
    onError: (error) => {
      console.error('Stream error:', error)
    },
  })
  
  return messages
}
```

## Advanced Features

### Multiple Model Support

```typescript
// app/api/chat/route.ts
import { anthropic } from '@ai-sdk/anthropic'
import { perplexity } from '@ai-sdk/perplexity'

export async function POST(req: Request) {
  const { messages, model } = await req.json()
  
  let aiModel
  switch (model) {
    case 'claude':
      aiModel = anthropic('claude-3-5-sonnet')
      break
    case 'perplexity':
      aiModel = perplexity('pplx-70b-online')
      break
    default:
      aiModel = openai('gpt-4-turbo')
  }
  
  const result = streamText({
    model: aiModel,
    messages,
    tools,
  })
  
  return result.toUIMessageStreamResponse()
}
```

### Server Actions (Next.js 15)

```typescript
// app/actions/chat.ts
'use server'

import { streamText } from 'ai'
import { createStreamableUI } from 'ai/rsc'

export async function sendMessage(message: string) {
  const stream = createStreamableUI()
  
  const result = streamText({
    model: openai('gpt-4-turbo'),
    messages: [{ role: 'user', content: message }],
    tools,
  })
  
  // Process stream and update UI
  for await (const part of result.fullStream) {
    if (part.type === 'text-delta') {
      stream.append(<span>{part.textDelta}</span>)
    } else if (part.type === 'tool-call') {
      stream.append(
        <ToolCall name={part.toolName} args={part.args} />
      )
    }
  }
  
  stream.done()
  return stream.value
}
```

### File Attachments

```typescript
// Support for file attachments in messages
const result = streamText({
  model: openai('gpt-4-vision'),
  messages: [{
    role: 'user',
    content: [
      { type: 'text', text: 'What is in this image?' },
      { 
        type: 'image', 
        image: await readFileAsDataURL(file),
      },
    ],
  }],
})
```

### Telemetry and Observability

```typescript
// Custom telemetry configuration
const result = streamText({
  model: openai('gpt-4-turbo'),
  messages,
  experimental_telemetry: {
    isEnabled: true,
    metadata: {
      userId: 'user-123',
      sessionId: 'session-456',
      environment: 'production',
    },
    functionId: 'chat-completion',
    recordInputs: true,
    recordOutputs: true,
  },
})
```

## Error Handling

```typescript
// Comprehensive error handling
try {
  const result = await streamText({
    model: openai('gpt-4-turbo'),
    messages,
    tools,
    maxRetries: 3,
    onError: (error) => {
      // Custom error handling
      if (error.code === 'rate_limit') {
        // Handle rate limiting
      }
    },
  })
} catch (error) {
  if (error instanceof AIError) {
    // Handle AI-specific errors
    console.error('AI Error:', error.code, error.message)
  } else {
    // Handle general errors
    console.error('General Error:', error)
  }
}
```

## Integration with TripSage Architecture

### Agent Coordination

```typescript
// Coordinate multiple agents with streaming
export async function coordinateAgents(request: TravelRequest) {
  const flightAgent = streamText({
    model: openai('gpt-4-turbo'),
    system: 'You are a flight search specialist...',
    messages: [{ role: 'user', content: request.flightRequirements }],
    tools: { searchFlights },
  })
  
  const accommodationAgent = streamText({
    model: openai('gpt-4-turbo'),
    system: 'You are an accommodation specialist...',
    messages: [{ role: 'user', content: request.accommodationRequirements }],
    tools: { searchAccommodations },
  })
  
  // Process streams in parallel
  const [flightResults, accommodationResults] = await Promise.all([
    processStream(flightAgent),
    processStream(accommodationAgent),
  ])
  
  return { flightResults, accommodationResults }
}
```

### Caching and Performance

```typescript
// Use with TanStack Query for caching
import { useQuery } from '@tanstack/react-query'

function useCachedCompletion(prompt: string) {
  return useQuery({
    queryKey: ['completion', prompt],
    queryFn: async () => {
      const response = await fetch('/api/complete', {
        method: 'POST',
        body: JSON.stringify({ prompt }),
      })
      return response.json()
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}
```

## Best Practices

1. **Stream Management**
   - Use `experimental_throttle` to control UI update frequency
   - Implement proper cleanup on component unmount
   - Handle connection errors gracefully

2. **Tool Design**
   - Keep tool functions focused and single-purpose
   - Use Zod for robust parameter validation
   - Return structured data for better parsing

3. **Performance**
   - Enable tool call streaming for better UX
   - Use appropriate model selection based on task
   - Implement caching for repeated queries

4. **Security**
   - Never expose API keys in client code
   - Validate all user inputs
   - Implement rate limiting
   - Use proper authentication

5. **Error Handling**
   - Provide user-friendly error messages
   - Implement retry logic for transient failures
   - Log errors for debugging

## Debugging

### Stream Inspection

```bash
# Use curl to inspect raw SSE stream
curl -N \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Hello"}]}' \
  http://localhost:3000/api/chat

# Use Node.js SSE client
npx sse-cat http://localhost:3000/api/chat
```

### Browser DevTools

1. Network tab → EventStream view for SSE inspection
2. Console for stream processing logs
3. React DevTools for component state

### Logging

```typescript
// Enable verbose logging
const result = streamText({
  model: openai('gpt-4-turbo'),
  messages,
  experimental_telemetry: {
    isEnabled: true,
    logLevel: 'debug',
  },
})
```

This integration ensures TripSage leverages the full power of Vercel AI SDK v5 for an exceptional AI-powered travel planning experience.