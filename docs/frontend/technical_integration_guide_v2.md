# TripSage Technical Integration Guide v2

This guide provides detailed implementation patterns and code examples for integrating the TripSage frontend with backend services using modern web technologies.

## 1. Vercel AI SDK Integration

### Setting Up AI SDK
```typescript
// app/api/chat/route.ts
import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { anthropic } from '@ai-sdk/anthropic';

export const runtime = 'edge';

export async function POST(req: Request) {
  const { messages, model = 'gpt-4-turbo' } = await req.json();
  
  // Model selection logic
  const selectedModel = model.startsWith('claude') 
    ? anthropic(model)
    : openai(model);
  
  const result = streamText({
    model: selectedModel,
    messages,
    temperature: 0.7,
    maxTokens: 4000,
    tools: {
      searchFlights: {
        description: 'Search for flights',
        parameters: z.object({
          from: z.string(),
          to: z.string(),
          date: z.string(),
        }),
        execute: async ({ from, to, date }) => {
          // Integration with flight search API
          return await searchFlights({ from, to, date });
        },
      },
      searchHotels: {
        description: 'Search for hotels',
        parameters: z.object({
          location: z.string(),
          checkIn: z.string(),
          checkOut: z.string(),
        }),
        execute: async ({ location, checkIn, checkOut }) => {
          // Integration with hotel search API
          return await searchHotels({ location, checkIn, checkOut });
        },
      },
    },
  });
  
  return result.toDataStreamResponse();
}
```

### Client-Side Chat Implementation
```typescript
// components/ChatInterface.tsx
'use client';

import { useChat } from 'ai/react';
import { useState } from 'react';
import { ModelSelector } from './ModelSelector';

export function ChatInterface() {
  const [model, setModel] = useState('gpt-4-turbo');
  
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
    body: {
      model,
    },
    onError: (error) => {
      console.error('Chat error:', error);
    },
  });
  
  return (
    <div className="flex flex-col h-full">
      <ModelSelector value={model} onChange={setModel} />
      
      <div className="flex-1 overflow-y-auto p-4">
        {messages.map((message) => (
          <div key={message.id} className={`mb-4 ${
            message.role === 'user' ? 'text-right' : 'text-left'
          }`}>
            <div className={`inline-block px-4 py-2 rounded-lg ${
              message.role === 'user' 
                ? 'bg-primary text-primary-foreground' 
                : 'bg-muted'
            }`}>
              {message.content}
            </div>
          </div>
        ))}
      </div>
      
      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={handleInputChange}
            placeholder="Ask about your travel plans..."
            className="flex-1 px-4 py-2 rounded-lg border"
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg disabled:opacity-50"
          >
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
```

## 2. MCP Integration

### MCP Client Setup
```typescript
// lib/mcp/client.ts
import { MCPClient } from '@/lib/mcp/base';
import { FlightsMCPClient } from '@/lib/mcp/flights';
import { HotelsMCPClient } from '@/lib/mcp/hotels';
import { WeatherMCPClient } from '@/lib/mcp/weather';

export class TripSageMCPManager {
  private clients: Map<string, MCPClient>;
  
  constructor() {
    this.clients = new Map([
      ['flights', new FlightsMCPClient()],
      ['hotels', new HotelsMCPClient()],
      ['weather', new WeatherMCPClient()],
    ]);
  }
  
  async invoke<T>(
    serverName: string,
    method: string,
    params: any
  ): Promise<T> {
    const client = this.clients.get(serverName);
    if (!client) {
      throw new Error(`Unknown MCP server: ${serverName}`);
    }
    
    return client.invoke(method, params);
  }
}

// Usage in API routes
export async function GET(request: Request) {
  const mcp = new TripSageMCPManager();
  
  const flights = await mcp.invoke('flights', 'search', {
    from: 'SFO',
    to: 'NYC',
    date: '2024-06-15',
  });
  
  return Response.json(flights);
}
```

### MCP Server Integration
```typescript
// lib/mcp/base.ts
export abstract class MCPClient {
  protected apiKey: string;
  protected baseUrl: string;
  
  constructor(config: MCPConfig) {
    this.apiKey = config.apiKey;
    this.baseUrl = config.baseUrl;
  }
  
  abstract invoke<T>(method: string, params: any): Promise<T>;
  
  protected async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
        ...options.headers,
      },
    });
    
    if (!response.ok) {
      throw new Error(`MCP request failed: ${response.statusText}`);
    }
    
    return response.json();
  }
}
```

## 3. Real-Time Agent Visualization

### WebSocket Connection
```typescript
// hooks/useAgentStatus.ts
import { useEffect, useState } from 'react';
import { io, Socket } from 'socket.io-client';

interface AgentStatus {
  id: string;
  name: string;
  status: 'idle' | 'thinking' | 'searching' | 'analyzing';
  progress: number;
  currentTask?: string;
}

export function useAgentStatus() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  
  useEffect(() => {
    const newSocket = io(process.env.NEXT_PUBLIC_WS_URL!, {
      transports: ['websocket'],
    });
    
    newSocket.on('agent:update', (update: AgentStatus) => {
      setAgents((prev) => {
        const index = prev.findIndex((a) => a.id === update.id);
        if (index >= 0) {
          const newAgents = [...prev];
          newAgents[index] = update;
          return newAgents;
        }
        return [...prev, update];
      });
    });
    
    newSocket.on('agent:remove', (agentId: string) => {
      setAgents((prev) => prev.filter((a) => a.id !== agentId));
    });
    
    setSocket(newSocket);
    
    return () => {
      newSocket.close();
    };
  }, []);
  
  return agents;
}
```

### Agent Flow Visualization
```typescript
// components/AgentFlowVisualization.tsx
import { ReactFlow, Node, Edge, Background } from 'reactflow';
import { useAgentFlow } from '@/hooks/useAgentFlow';
import 'reactflow/dist/style.css';

export function AgentFlowVisualization() {
  const { nodes, edges, onNodesChange, onEdgesChange } = useAgentFlow();
  
  const nodeTypes = {
    agent: AgentNode,
    task: TaskNode,
    result: ResultNode,
  };
  
  return (
    <div className="h-[500px] w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
      >
        <Background variant="dots" gap={12} size={1} />
      </ReactFlow>
    </div>
  );
}

// Custom node component
function AgentNode({ data }: { data: AgentNodeData }) {
  return (
    <div className="px-4 py-2 bg-card border border-border rounded-lg">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${
          data.status === 'active' ? 'bg-green-500 animate-pulse' : 'bg-gray-500'
        }`} />
        <span className="font-medium">{data.label}</span>
      </div>
      {data.task && (
        <div className="text-sm text-muted-foreground mt-1">
          {data.task}
        </div>
      )}
    </div>
  );
}
```

## 4. Streaming Responses

### Server-Side Streaming
```typescript
// app/api/stream/route.ts
export async function GET() {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Simulate streaming data
      const messages = [
        'Searching for flights...',
        'Found 23 available flights',
        'Analyzing prices...',
        'Checking hotel availability...',
        'Found 15 hotels near your destination',
        'Creating itinerary...',
        'Trip planning complete!',
      ];
      
      for (const message of messages) {
        controller.enqueue(encoder.encode(`data: ${message}\n\n`));
        await new Promise((resolve) => setTimeout(resolve, 1000));
      }
      
      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      controller.close();
    },
  });
  
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

### Client-Side Streaming
```typescript
// hooks/useStreamingData.ts
export function useStreamingData(url: string) {
  const [data, setData] = useState<string[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  
  useEffect(() => {
    const eventSource = new EventSource(url);
    setIsStreaming(true);
    
    eventSource.onmessage = (event) => {
      if (event.data === '[DONE]') {
        eventSource.close();
        setIsStreaming(false);
        return;
      }
      
      setData((prev) => [...prev, event.data]);
    };
    
    eventSource.onerror = () => {
      eventSource.close();
      setIsStreaming(false);
    };
    
    return () => {
      eventSource.close();
    };
  }, [url]);
  
  return { data, isStreaming };
}
```

## 5. State Management

### Zustand Store with TypeScript
```typescript
// stores/travelStore.ts
import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import { devtools, persist } from 'zustand/middleware';

interface TravelPlan {
  id: string;
  destination: string;
  startDate: Date;
  endDate: Date;
  budget: number;
  activities: Activity[];
  accommodations: Accommodation[];
  transportation: Transportation[];
}

interface TravelStore {
  currentPlan: TravelPlan | null;
  plans: TravelPlan[];
  isLoading: boolean;
  error: string | null;
  
  // Actions
  createPlan: (plan: Partial<TravelPlan>) => Promise<void>;
  updatePlan: (id: string, updates: Partial<TravelPlan>) => void;
  deletePlan: (id: string) => void;
  loadPlans: () => Promise<void>;
}

export const useTravelStore = create<TravelStore>()(
  devtools(
    persist(
      immer((set, get) => ({
        currentPlan: null,
        plans: [],
        isLoading: false,
        error: null,
        
        createPlan: async (planData) => {
          set((state) => {
            state.isLoading = true;
            state.error = null;
          });
          
          try {
            const response = await fetch('/api/plans', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(planData),
            });
            
            if (!response.ok) throw new Error('Failed to create plan');
            
            const newPlan = await response.json();
            
            set((state) => {
              state.plans.push(newPlan);
              state.currentPlan = newPlan;
              state.isLoading = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error.message;
              state.isLoading = false;
            });
          }
        },
        
        updatePlan: (id, updates) =>
          set((state) => {
            const index = state.plans.findIndex((p) => p.id === id);
            if (index !== -1) {
              state.plans[index] = { ...state.plans[index], ...updates };
              if (state.currentPlan?.id === id) {
                state.currentPlan = { ...state.currentPlan, ...updates };
              }
            }
          }),
          
        deletePlan: (id) =>
          set((state) => {
            state.plans = state.plans.filter((p) => p.id !== id);
            if (state.currentPlan?.id === id) {
              state.currentPlan = null;
            }
          }),
          
        loadPlans: async () => {
          set((state) => {
            state.isLoading = true;
          });
          
          try {
            const response = await fetch('/api/plans');
            const plans = await response.json();
            
            set((state) => {
              state.plans = plans;
              state.isLoading = false;
            });
          } catch (error) {
            set((state) => {
              state.error = error.message;
              state.isLoading = false;
            });
          }
        },
      })),
      {
        name: 'travel-store',
      }
    )
  )
);
```

## 6. Error Handling

### Global Error Boundary
```typescript
// app/error.tsx
'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error(error);
  }, [error]);
  
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] gap-4">
      <h2 className="text-2xl font-bold">Something went wrong!</h2>
      <p className="text-muted-foreground">
        {error.message || 'An unexpected error occurred'}
      </p>
      <Button onClick={reset}>Try again</Button>
    </div>
  );
}
```

### API Error Handler
```typescript
// lib/api/errorHandler.ts
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public code?: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export async function handleApiError(error: unknown): Promise<Response> {
  console.error('API Error:', error);
  
  if (error instanceof ApiError) {
    return Response.json(
      {
        error: error.message,
        code: error.code,
      },
      { status: error.statusCode }
    );
  }
  
  if (error instanceof Error) {
    return Response.json(
      {
        error: error.message,
      },
      { status: 500 }
    );
  }
  
  return Response.json(
    {
      error: 'An unexpected error occurred',
    },
    { status: 500 }
  );
}
```

## 7. Authentication & Security

### API Key Management
```typescript
// hooks/useApiKeys.ts
import { useState, useEffect } from 'react';
import { encrypt, decrypt } from '@/lib/crypto';

interface ApiKeys {
  openai?: string;
  anthropic?: string;
  googleMaps?: string;
  // Add more providers as needed
}

export function useApiKeys() {
  const [keys, setKeys] = useState<ApiKeys>({});
  const [isLoaded, setIsLoaded] = useState(false);
  
  useEffect(() => {
    // Load encrypted keys from localStorage
    const storedKeys = localStorage.getItem('encrypted_api_keys');
    if (storedKeys) {
      try {
        const decrypted = decrypt(storedKeys);
        setKeys(JSON.parse(decrypted));
      } catch (error) {
        console.error('Failed to decrypt API keys:', error);
      }
    }
    setIsLoaded(true);
  }, []);
  
  const saveKey = (provider: keyof ApiKeys, key: string) => {
    const updatedKeys = { ...keys, [provider]: key };
    setKeys(updatedKeys);
    
    // Encrypt and store
    const encrypted = encrypt(JSON.stringify(updatedKeys));
    localStorage.setItem('encrypted_api_keys', encrypted);
  };
  
  const removeKey = (provider: keyof ApiKeys) => {
    const updatedKeys = { ...keys };
    delete updatedKeys[provider];
    setKeys(updatedKeys);
    
    // Update storage
    const encrypted = encrypt(JSON.stringify(updatedKeys));
    localStorage.setItem('encrypted_api_keys', encrypted);
  };
  
  const validateKey = async (provider: keyof ApiKeys, key: string) => {
    // Implement provider-specific validation
    switch (provider) {
      case 'openai':
        return validateOpenAIKey(key);
      case 'anthropic':
        return validateAnthropicKey(key);
      // Add more providers
      default:
        return false;
    }
  };
  
  return {
    keys,
    isLoaded,
    saveKey,
    removeKey,
    validateKey,
  };
}
```

### Secure Communication
```typescript
// lib/crypto.ts
export function encrypt(text: string): string {
  // Use Web Crypto API for client-side encryption
  // This is a simplified example - use proper encryption in production
  const encoder = new TextEncoder();
  const data = encoder.encode(text);
  
  // In production, use a proper encryption key
  const key = process.env.NEXT_PUBLIC_ENCRYPTION_KEY;
  
  // Implement actual encryption logic
  return btoa(String.fromCharCode(...data));
}

export function decrypt(encryptedText: string): string {
  // Implement decryption logic
  const decodedData = atob(encryptedText);
  const charData = decodedData.split('').map((x) => x.charCodeAt(0));
  const decoder = new TextDecoder();
  return decoder.decode(new Uint8Array(charData));
}
```

## 8. Testing

### Component Testing
```typescript
// __tests__/components/ChatInterface.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ChatInterface } from '@/components/ChatInterface';
import { useChat } from 'ai/react';

jest.mock('ai/react', () => ({
  useChat: jest.fn(),
}));

describe('ChatInterface', () => {
  const mockHandleSubmit = jest.fn();
  const mockHandleInputChange = jest.fn();
  
  beforeEach(() => {
    (useChat as jest.Mock).mockReturnValue({
      messages: [
        { id: '1', role: 'user', content: 'Hello' },
        { id: '2', role: 'assistant', content: 'Hi there!' },
      ],
      input: '',
      handleInputChange: mockHandleInputChange,
      handleSubmit: mockHandleSubmit,
      isLoading: false,
    });
  });
  
  it('renders messages correctly', () => {
    render(<ChatInterface />);
    
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });
  
  it('handles form submission', async () => {
    render(<ChatInterface />);
    
    const input = screen.getByPlaceholderText('Ask about your travel plans...');
    const button = screen.getByText('Send');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockHandleSubmit).toHaveBeenCalled();
    });
  });
});
```

### Integration Testing
```typescript
// __tests__/api/chat.test.ts
import { POST } from '@/app/api/chat/route';
import { OpenAIStream } from 'ai';

jest.mock('ai', () => ({
  OpenAIStream: jest.fn(),
  StreamingTextResponse: jest.fn((stream) => ({
    stream,
  })),
}));

describe('/api/chat', () => {
  it('handles chat requests correctly', async () => {
    const mockRequest = new Request('http://localhost:3000/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        messages: [{ role: 'user', content: 'Hello' }],
        model: 'gpt-4-turbo',
      }),
    });
    
    const response = await POST(mockRequest);
    
    expect(OpenAIStream).toHaveBeenCalled();
    expect(response).toBeDefined();
  });
});
```

## 9. Deployment

### Environment Variables
```env
# Development (.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8001
NEXT_PUBLIC_MAPBOX_TOKEN=your_dev_token

# Production (Vercel Environment Variables)
NEXT_PUBLIC_API_URL=https://api.tripsage.ai
NEXT_PUBLIC_WS_URL=wss://ws.tripsage.ai
NEXT_PUBLIC_MAPBOX_TOKEN=your_prod_token
```

### Docker Configuration
```dockerfile
# Dockerfile
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

## Conclusion

This technical integration guide provides comprehensive patterns and implementations for building the TripSage frontend. By following these patterns and leveraging the latest web technologies, you can create a robust, scalable, and performant travel planning application.

Remember to:
- Keep components small and focused
- Use TypeScript for better type safety
- Implement proper error handling
- Add comprehensive testing
- Monitor performance and user experience
- Follow security best practices
- Document your code and APIs

For more specific implementation details, refer to the individual technology documentation and the TripSage API specifications.