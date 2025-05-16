# MCP SDK Integration Guide for TripSage Frontend

This guide covers the integration of Model Context Protocol (MCP) TypeScript SDK with Next.js 15 for real-time agent communication and tool execution, based on the latest MCP specification.

## Architecture Overview

MCP follows a layered architecture with clear separation of concerns:

### Protocol Layer
- Based on JSON-RPC 2.0 for message formatting
- Handles request/response matching and error reporting
- Supports outgoing requests and one-way notifications

### Transport Layer
- **STDIO**: For local process-based communication
- **WebSocket**: For bidirectional real-time communication
- **SSE (Server-Sent Events)**: For server-to-client streaming
- **HTTP**: For stateless request-response

### Client-Server Architecture
- **MCP Client**: Initiates connections, manages sessions
- **MCP Server**: Exposes tools, resources, and prompts
- **Sessions**: Manage communication patterns between client and server

## Setup

### 1. Install Dependencies

```bash
pnpm add @modelcontextprotocol/typescript-sdk zod
```

### 2. MCP Client Implementation

```typescript
// lib/mcp/client.ts
import { Client } from '@modelcontextprotocol/typescript-sdk/client'
import { WebSocketTransport } from '@modelcontextprotocol/typescript-sdk/transport/websocket'
import { z } from 'zod'

export class TripSageMCPClient {
  private client: Client
  private transport: WebSocketTransport
  
  constructor(private wsUrl: string) {
    this.transport = new WebSocketTransport(wsUrl)
    this.client = new Client({
      name: 'tripsage-frontend',
      version: '1.0.0',
    })
  }
  
  async connect() {
    await this.client.connect(this.transport)
    
    // Set up event handlers
    this.client.on('notification', this.handleNotification)
    this.client.on('error', this.handleError)
  }
  
  async disconnect() {
    await this.client.close()
  }
  
  // Tool execution with type safety
  async executeTool<T>(name: string, args: Record<string, any>, schema: z.ZodSchema<T>) {
    const validated = schema.parse(args)
    const result = await this.client.invoke('tools/execute', {
      name,
      arguments: validated,
    })
    return result
  }
  
  // Resource access
  async getResource(uri: string) {
    return await this.client.invoke('resources/read', { uri })
  }
  
  private handleNotification = (notification: any) => {
    console.log('MCP notification:', notification)
    // Handle agent updates, progress, etc.
  }
  
  private handleError = (error: Error) => {
    console.error('MCP error:', error)
    // Implement error recovery
  }
}
```

### 3. Transport Configuration

```typescript
// lib/mcp/transports.ts
import { StdioTransport } from '@modelcontextprotocol/typescript-sdk/transport/stdio'
import { SSETransport } from '@modelcontextprotocol/typescript-sdk/transport/sse'
import { HttpTransport } from '@modelcontextprotocol/typescript-sdk/transport/http'

export function createTransport(type: 'websocket' | 'stdio' | 'sse' | 'http', config: any) {
  switch (type) {
    case 'websocket':
      return new WebSocketTransport(config.url)
    
    case 'stdio':
      return new StdioTransport(config.command, config.args)
    
    case 'sse':
      return new SSETransport(config.url)
    
    case 'http':
      return new HttpTransport(config.url)
    
    default:
      throw new Error(`Unknown transport type: ${type}`)
  }
}
```

### 4. React Hook for MCP

```typescript
// hooks/useMCP.ts
import { useEffect, useState, useCallback } from 'react'
import { TripSageMCPClient } from '@/lib/mcp/client'
import { z } from 'zod'

interface MCPState {
  client: TripSageMCPClient | null
  connected: boolean
  error: Error | null
  agentUpdates: Map<string, any>
}

export function useMCP(wsUrl: string) {
  const [state, setState] = useState<MCPState>({
    client: null,
    connected: false,
    error: null,
    agentUpdates: new Map(),
  })
  
  useEffect(() => {
    const client = new TripSageMCPClient(wsUrl)
    
    client.connect()
      .then(() => {
        setState(prev => ({
          ...prev,
          client,
          connected: true,
        }))
      })
      .catch(error => {
        setState(prev => ({
          ...prev,
          error,
        }))
      })
    
    return () => {
      client.disconnect()
    }
  }, [wsUrl])
  
  const executeTool = useCallback(
    async <T>(name: string, args: any, schema: z.ZodSchema<T>) => {
      if (!state.client) throw new Error('MCP client not connected')
      return await state.client.executeTool(name, args, schema)
    },
    [state.client]
  )
  
  return {
    ...state,
    executeTool,
  }
}
```

### 5. Tool Definitions with Zod

```typescript
// lib/mcp/schemas.ts
import { z } from 'zod'

export const FlightSearchSchema = z.object({
  origin: z.string().min(3).max(3),
  destination: z.string().min(3).max(3),
  departureDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  returnDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  passengers: z.number().min(1).max(9).default(1),
  class: z.enum(['economy', 'business', 'first']).default('economy'),
})

export const AccommodationSearchSchema = z.object({
  location: z.string().min(1),
  checkIn: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  checkOut: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  guests: z.number().min(1).max(10),
  priceRange: z.object({
    min: z.number().min(0),
    max: z.number().min(0),
  }).optional(),
})

export const WeatherRequestSchema = z.object({
  location: z.string().min(1),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  units: z.enum(['metric', 'imperial']).default('metric'),
})

export type FlightSearchInput = z.infer<typeof FlightSearchSchema>
export type AccommodationSearchInput = z.infer<typeof AccommodationSearchSchema>
export type WeatherRequestInput = z.infer<typeof WeatherRequestSchema>
```

### 6. MCP Tool Component

```typescript
// components/features/MCPToolExecutor.tsx
'use client'

import { useState } from 'react'
import { useMCP } from '@/hooks/useMCP'
import { FlightSearchSchema, FlightSearchInput } from '@/lib/mcp/schemas'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Loader2 } from 'lucide-react'

export function MCPToolExecutor() {
  const { connected, executeTool } = useMCP(process.env.NEXT_PUBLIC_MCP_WS_URL!)
  const [executing, setExecuting] = useState(false)
  const [results, setResults] = useState<any>(null)
  
  async function searchFlights() {
    setExecuting(true)
    try {
      const searchParams: FlightSearchInput = {
        origin: 'JFK',
        destination: 'LAX',
        departureDate: '2025-03-01',
        passengers: 2,
        class: 'economy',
      }
      
      const result = await executeTool(
        'search_flights',
        searchParams,
        FlightSearchSchema
      )
      
      setResults(result)
    } catch (error) {
      console.error('Flight search error:', error)
    } finally {
      setExecuting(false)
    }
  }
  
  if (!connected) {
    return (
      <Card className="p-6">
        <div className="flex items-center gap-2">
          <Loader2 className="animate-spin" />
          <span>Connecting to MCP server...</span>
        </div>
      </Card>
    )
  }
  
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">MCP Tool Executor</h3>
      
      <Button
        onClick={searchFlights}
        disabled={executing}
        className="w-full"
      >
        {executing ? (
          <>
            <Loader2 className="mr-2 animate-spin" />
            Searching Flights...
          </>
        ) : (
          'Search Flights JFK → LAX'
        )}
      </Button>
      
      {results && (
        <div className="mt-4">
          <h4 className="font-medium mb-2">Results:</h4>
          <pre className="p-4 bg-muted rounded overflow-auto text-sm">
            {JSON.stringify(results, null, 2)}
          </pre>
        </div>
      )}
    </Card>
  )
}
```

### 7. Real-time Agent Updates

```typescript
// components/features/AgentStatusMonitor.tsx
'use client'

import { useEffect, useState } from 'react'
import { Card } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { motion, AnimatePresence } from 'framer-motion'

interface AgentUpdate {
  agentId: string
  status: 'idle' | 'thinking' | 'executing' | 'completed' | 'error'
  progress?: number
  message?: string
  timestamp: Date
}

export function AgentStatusMonitor() {
  const [updates, setUpdates] = useState<Map<string, AgentUpdate>>(new Map())
  
  useEffect(() => {
    // Connect to SSE endpoint for real-time updates
    const eventSource = new EventSource('/api/mcp/sse')
    
    eventSource.onmessage = (event) => {
      try {
        const update: AgentUpdate = JSON.parse(event.data)
        setUpdates(prev => new Map(prev).set(update.agentId, update))
      } catch (error) {
        console.error('SSE parse error:', error)
      }
    }
    
    eventSource.onerror = (error) => {
      console.error('SSE error:', error)
    }
    
    return () => {
      eventSource.close()
    }
  }, [])
  
  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">Agent Activity</h3>
      
      <AnimatePresence>
        {Array.from(updates.values()).map(update => (
          <motion.div
            key={update.agentId}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-4 p-4 border rounded-lg"
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="font-medium">{update.agentId}</span>
                <Badge variant={
                  update.status === 'completed' ? 'success' :
                  update.status === 'error' ? 'destructive' :
                  'default'
                }>
                  {update.status}
                </Badge>
              </div>
              <span className="text-sm text-muted-foreground">
                {new Date(update.timestamp).toLocaleTimeString()}
              </span>
            </div>
            
            {update.progress !== undefined && (
              <Progress value={update.progress} className="mb-2" />
            )}
            
            {update.message && (
              <p className="text-sm text-muted-foreground">{update.message}</p>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </Card>
  )
}
```

### 8. Error Handling and Resilience

```typescript
// lib/mcp/resilient-client.ts
export class ResilientMCPClient extends TripSageMCPClient {
  private reconnectAttempts = 0
  private readonly maxReconnectAttempts = 5
  private readonly initialDelay = 1000
  private reconnectTimer?: NodeJS.Timeout
  
  async connect() {
    try {
      await super.connect()
      this.reconnectAttempts = 0
    } catch (error) {
      await this.handleConnectionError(error)
    }
  }
  
  private async handleConnectionError(error: any) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      throw new Error('Max reconnection attempts reached')
    }
    
    this.reconnectAttempts++
    const delay = this.initialDelay * Math.pow(2, this.reconnectAttempts - 1)
    
    console.log(`Reconnecting in ${delay}ms... (attempt ${this.reconnectAttempts})`)
    
    await new Promise(resolve => {
      this.reconnectTimer = setTimeout(resolve, delay)
    })
    
    return this.connect()
  }
  
  async disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
    }
    await super.disconnect()
  }
}
```

### 9. Integration with Zustand Store

```typescript
// stores/mcpStore.ts
import { create } from 'zustand'
import { ResilientMCPClient } from '@/lib/mcp/resilient-client'

interface MCPStore {
  client: ResilientMCPClient | null
  connected: boolean
  connecting: boolean
  error: Error | null
  agentStates: Map<string, any>
  
  connect: (wsUrl: string) => Promise<void>
  disconnect: () => Promise<void>
  updateAgentState: (agentId: string, state: any) => void
}

export const useMCPStore = create<MCPStore>((set, get) => ({
  client: null,
  connected: false,
  connecting: false,
  error: null,
  agentStates: new Map(),
  
  connect: async (wsUrl: string) => {
    set({ connecting: true, error: null })
    
    try {
      const client = new ResilientMCPClient(wsUrl)
      await client.connect()
      
      set({
        client,
        connected: true,
        connecting: false,
      })
    } catch (error) {
      set({
        error: error as Error,
        connecting: false,
      })
    }
  },
  
  disconnect: async () => {
    const { client } = get()
    if (client) {
      await client.disconnect()
      set({
        client: null,
        connected: false,
      })
    }
  },
  
  updateAgentState: (agentId: string, state: any) => {
    set(store => ({
      agentStates: new Map(store.agentStates).set(agentId, state),
    }))
  },
}))
```

## Best Practices

### 1. Transport Selection
- Use WebSocket for real-time bidirectional communication
- Use SSE for server-to-client streaming (agent updates)
- Use HTTP for simple request-response patterns
- Use STDIO for local development and testing

### 2. Type Safety
- Define Zod schemas for all tool inputs and outputs
- Use TypeScript generics for type-safe tool execution
- Validate all data at runtime with schemas

### 3. Error Handling
- Implement exponential backoff for reconnection
- Provide user feedback for connection issues
- Handle both transport and protocol errors gracefully

### 4. Performance
- Use connection pooling for multiple MCP servers
- Implement request debouncing for frequent operations
- Cache tool listings and resource metadata

### 5. Security
- Always use WSS/HTTPS in production
- Validate all inputs on both client and server
- Implement proper authentication and authorization
- Never expose sensitive data in error messages

## Integration with TripSage Architecture

The MCP SDK integrates with TripSage's architecture through the abstraction layer:

```typescript
// lib/mcp/tripsage-integration.ts
import { ResilientMCPClient } from './resilient-client'
import { useMCPStore } from '@/stores/mcpStore'

export class TripSageMCPManager {
  private clients: Map<string, ResilientMCPClient> = new Map()
  
  async connectToServer(name: string, wsUrl: string) {
    const client = new ResilientMCPClient(wsUrl)
    await client.connect()
    this.clients.set(name, client)
  }
  
  async executeTool(serverName: string, toolName: string, args: any, schema: any) {
    const client = this.clients.get(serverName)
    if (!client) throw new Error(`No client for server: ${serverName}`)
    
    return await client.executeTool(toolName, args, schema)
  }
  
  async disconnectAll() {
    for (const client of this.clients.values()) {
      await client.disconnect()
    }
    this.clients.clear()
  }
}

// Singleton instance
export const mcpManager = new TripSageMCPManager()
```

This implementation ensures reliable, type-safe communication between TripSage's frontend and the various MCP servers used by the backend.