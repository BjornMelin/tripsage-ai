# Required Code Changes for TripSage Implementation

This document outlines the necessary code changes required to implement the complete TripSage system based on the documented architecture and specifications.

## Core Architecture Changes

### 1. MCP Server Integration

The existing implementation is built around OpenAI's Assistants API, but our architecture requires a shift to MCP servers. The following changes are needed:

#### BaseAgent Class Refactoring

Current location: `/src/agents/base_agent.py`

The current `BaseAgent` implementation needs to be refactored to:

1. Replace direct OpenAI Assistant API dependency with MCP server integrations
2. Implement the dual storage architecture (Supabase + Knowledge Graph)
3. Add support for sequential thinking and planning capabilities

```python
# New imports required
from memory import MemoryClient  # Knowledge Graph client
from sequential_thinking import SequentialThinking
from time_management import TimeManager
from supabase import create_client

class BaseAgent:
    """Base class for all TripSage agents with MCP server integration"""

    def __init__(
        self,
        name: str,
        instructions: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        # Initialize existing properties
        self.name = name
        self.instructions = instructions
        self.tools = tools or []
        self.model = model or config.model_name
        self.metadata = metadata or {"agent_type": "tripsage"}
        
        # Initialize MCP clients
        self.memory_client = MemoryClient(config.memory_endpoint)
        self.sequential_thinking = SequentialThinking()
        self.time_manager = TimeManager()
        
        # Initialize dual storage
        self.supabase = create_client(config.supabase_url, config.supabase_key)
        
        # Track conversation state
        self.messages_history = []
```

#### Tool Interface Standardization

Create a new module to standardize tool interfaces across MCP servers:

```python
# New file: /src/agents/tool_interface.py
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

@runtime_checkable
class MCPTool(Protocol):
    """Protocol defining the standard interface for all MCP tools"""
    
    name: str
    description: str
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with the given parameters"""
        ...
```

### 2. New MCP Server Implementation

Create dedicated modules for each MCP server:

#### Google Maps MCP Server

```python
# New file: /src/mcp/google_maps_mcp.py
from tool_interface import MCPTool
import httpx
from typing import Any, Dict, List

class GoogleMapsGeocoding(MCPTool):
    name = "google_maps_geocoding"
    description = "Convert addresses to geographic coordinates"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...

class GoogleMapsPlaces(MCPTool):
    name = "google_maps_places"
    description = "Search for places and points of interest"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...

class GoogleMapsDirections(MCPTool):
    name = "google_maps_directions"
    description = "Get directions between locations"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...
```

#### Airbnb MCP Server

```python
# New file: /src/mcp/airbnb_mcp.py
from tool_interface import MCPTool
import httpx
from playwright.async_api import async_playwright
from typing import Any, Dict, List

class AirbnbSearch(MCPTool):
    name = "airbnb_search"
    description = "Search for accommodations on Airbnb"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation using Playwright for HTML parsing
        ...

class AirbnbGetListing(MCPTool):
    name = "airbnb_get_listing"
    description = "Get detailed information about an Airbnb listing"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...
```

#### Time MCP Server

```python
# New file: /src/mcp/time_mcp.py
from tool_interface import MCPTool
from typing import Any, Dict, List
from datetime import datetime
import pendulum

class TimeConversion(MCPTool):
    name = "time_conversion"
    description = "Convert times between time zones"
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation using pendulum for timezone handling
        ...

class TimeCalculation(MCPTool):
    name = "time_calculation"
    description = "Calculate time differences, durations, etc."
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        # Implementation
        ...
```

### 3. Knowledge Graph Implementation

```python
# New file: /src/memory/knowledge_graph.py
from typing import Any, Dict, List, Optional
import httpx
from config import config

class MemoryClient:
    """Client for interacting with the Knowledge Graph MCP Server"""
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.api_key = config.memory_api_key
        
    async def create_entities(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create new entities in the knowledge graph"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/entities",
                json={"entities": entities},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
            
    async def create_relations(self, relations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create relations between entities in the knowledge graph"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/relations",
                json={"relations": relations},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
            
    async def search_nodes(self, query: str) -> Dict[str, Any]:
        """Search for nodes in the knowledge graph"""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.endpoint}/search",
                params={"query": query},
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
```

### 4. Sequential Thinking Implementation

```python
# New file: /src/agents/sequential_thinking.py
from typing import Any, Dict, List, Optional
import httpx
from config import config

class SequentialThinking:
    """Integration with Sequential Thinking MCP Server for complex planning"""
    
    def __init__(self):
        self.endpoint = config.sequential_thinking_endpoint
        self.api_key = config.sequential_thinking_api_key
        
    async def plan(self, problem: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Plan a solution to a complex problem using sequential thinking"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.endpoint}/plan",
                json={
                    "problem": problem,
                    "context": context,
                    "total_thoughts": 10,  # Default, can be adjusted
                },
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            return response.json()
```

## API Layer Changes

### 1. New API Routes

Add new routes to the FastAPI application to support the MCP server architecture:

```python
# New file: /src/api/routes/knowledge.py
from fastapi import APIRouter, Depends, HTTPException
from auth import get_current_active_user
from memory.knowledge_graph import MemoryClient
from typing import Any, Dict, List

router = APIRouter(
    prefix="/knowledge",
    tags=["knowledge"],
    dependencies=[Depends(get_current_active_user)],
)

@router.get("/search")
async def search_knowledge(query: str):
    """Search the knowledge graph"""
    memory_client = MemoryClient(config.memory_endpoint)
    results = await memory_client.search_nodes(query)
    return results

@router.post("/entities")
async def create_entities(entities: List[Dict[str, Any]]):
    """Create new entities in the knowledge graph"""
    memory_client = MemoryClient(config.memory_endpoint)
    result = await memory_client.create_entities(entities)
    return result
```

### 2. Update main.py

Update the main FastAPI application to include the new routers:

```python
# Updated file: /src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, flights, trips, users, knowledge, maps, accommodations, time_management

# Update FastAPI app
app = FastAPI(
    title="TripSage API",
    description="API for TripSage travel planning system with MCP server integration",
    version="0.2.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(flights.router)
app.include_router(knowledge.router)
app.include_router(maps.router)
app.include_router(accommodations.router)
app.include_router(time_management.router)
```

## Database Schema Updates

### 1. New Tables for Dual Storage

Add new tables to the Supabase schema to support the dual storage architecture:

```sql
-- New migration file: /migrations/20250509_01_knowledge_integration.sql

-- Table for tracking knowledge graph entities
CREATE TABLE IF NOT EXISTS kg_entities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    name TEXT NOT NULL,
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT kg_entities_entity_id_unique UNIQUE (entity_id)
);

COMMENT ON TABLE kg_entities IS 'Knowledge graph entities referenced in the relational database';

-- Table for caching
CREATE TABLE IF NOT EXISTS cache_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    cache_key TEXT NOT NULL,
    cache_value JSONB NOT NULL,
    source TEXT NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT cache_items_key_source_unique UNIQUE (cache_key, source)
);

COMMENT ON TABLE cache_items IS 'Cache for API results and computed data';

-- Add search history table
CREATE TABLE IF NOT EXISTS search_history (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    search_type TEXT NOT NULL,
    search_params JSONB NOT NULL,
    results_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT search_history_type_check CHECK (search_type IN ('flight', 'accommodation', 'activity', 'destination'))
);

COMMENT ON TABLE search_history IS 'History of user searches for analytics and recommendations';
```

### 2. Add TypeScript Types

Add TypeScript types to match the updated database schema:

```typescript
// Updated file: /src/types/supabase.ts
export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      users: {
        Row: {
          id: number
          name: string | null
          email: string
          preferences_json: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          name?: string | null
          email: string
          preferences_json?: Json | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: number
          name?: string | null
          email?: string
          preferences_json?: Json | null
          created_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      trips: {
        Row: {
          id: number
          name: string
          start_date: string
          end_date: string
          destination: string
          budget: number
          travelers: number
          status: string
          trip_type: string
          flexibility: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          name: string
          start_date: string
          end_date: string
          destination: string
          budget: number
          travelers: number
          status: string
          trip_type: string
          flexibility?: Json | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: number
          name?: string
          start_date?: string
          end_date?: string
          destination?: string
          budget?: number
          travelers?: number
          status?: string
          trip_type?: string
          flexibility?: Json | null
          created_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      kg_entities: {
        Row: {
          id: number
          entity_id: string
          entity_type: string
          name: string
          properties: Json | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: number
          entity_id: string
          entity_type: string
          name: string
          properties?: Json | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: number
          entity_id?: string
          entity_type?: string
          name?: string
          properties?: Json | null
          created_at?: string
          updated_at?: string
        }
        Relationships: []
      }
      // Additional tables omitted for brevity
    }
    // Views, functions, etc. omitted for brevity
  }
}
```

## TravelAgent Class Updates

Update the TravelAgent class to use the new MCP server architecture:

```python
# Updated file: /src/agents/travel_agent.py
from typing import Any, Dict, List, Optional
from base_agent import BaseAgent
from config import config
from memory.knowledge_graph import MemoryClient
from mcp.google_maps_mcp import GoogleMapsGeocoding, GoogleMapsPlaces
from mcp.airbnb_mcp import AirbnbSearch
from mcp.time_mcp import TimeConversion
from supabase import create_client

class TravelAgent(BaseAgent):
    """
    Primary travel planning agent that coordinates the planning process
    using the MCP server architecture.
    """

    def __init__(self):
        instructions = """
        You are a travel planning assistant for TripSage. Your role is to help users plan their travels...
        """

        # Initialize base agent
        super().__init__(
            name="TripSage Travel Planner",
            instructions=instructions,
            metadata={"agent_type": "travel_planner", "version": "2.0.0"},
        )
        
        # Initialize MCP tools
        self.mcp_tools = {
            "google_maps_geocoding": GoogleMapsGeocoding(),
            "google_maps_places": GoogleMapsPlaces(),
            "airbnb_search": AirbnbSearch(),
            "time_conversion": TimeConversion(),
            # Additional tools
        }
        
    async def process_message(self, message: str, user_id: str) -> str:
        """Process a user message and return a response"""
        # Add message to history
        self.add_message(message)
        
        # Create context from knowledge graph
        context = await self._build_context(user_id)
        
        # Use sequential thinking for complex queries
        if self._is_complex_query(message):
            plan = await self.sequential_thinking.plan(message, context)
            # Execute the plan
            response = await self._execute_plan(plan)
        else:
            # Simple query handling
            response = await self._handle_simple_query(message, context)
            
        # Update knowledge graph with new information
        await self._update_knowledge(user_id, message, response)
        
        return response
        
    async def _build_context(self, user_id: str) -> Dict[str, Any]:
        """Build context from knowledge graph and Supabase"""
        # Get user data from Supabase
        user_data = await self._get_user_data(user_id)
        
        # Get relevant knowledge from memory
        memory_client = MemoryClient(config.memory_endpoint)
        knowledge = await memory_client.search_nodes(f"user:{user_id}")
        
        return {
            "user_data": user_data,
            "knowledge": knowledge,
            "travel_preferences": user_data.get("preferences_json", {})
        }
        
    async def _handle_tool_call(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call using the appropriate MCP server"""
        if tool_name in self.mcp_tools:
            return await self.mcp_tools[tool_name].execute(args)
        
        # Fall back to standard tools for backward compatibility
        if tool_name == "search_flights":
            return await self._search_flights(args)
        elif tool_name == "search_accommodations":
            return await self._search_accommodations(args)
        elif tool_name == "search_activities":
            return await self._search_activities(args)
        elif tool_name == "create_trip":
            return await self._create_trip(args)
        else:
            return {"error": f"Unknown tool: {tool_name}"}
```

## Configuration Updates

Update the configuration to include the new MCP server endpoints:

```python
# Updated file: /src/agents/config.py
import os
from pydantic import BaseSettings, Field

class Settings(BaseSettings):
    """Application settings"""
    
    # OpenAI settings (legacy)
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")
    model_name: str = "gpt-4"
    
    # Supabase settings
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_key: str = Field(..., env="SUPABASE_ANON_KEY")
    
    # MCP server endpoints
    memory_endpoint: str = Field(..., env="MEMORY_MCP_ENDPOINT")
    memory_api_key: str = Field(..., env="MEMORY_MCP_API_KEY")
    
    google_maps_endpoint: str = Field(..., env="GOOGLE_MAPS_MCP_ENDPOINT") 
    google_maps_api_key: str = Field(..., env="GOOGLE_MAPS_MCP_API_KEY")
    
    airbnb_endpoint: str = Field(..., env="AIRBNB_MCP_ENDPOINT")
    airbnb_api_key: str = Field(..., env="AIRBNB_MCP_API_KEY")
    
    time_endpoint: str = Field(..., env="TIME_MCP_ENDPOINT")
    time_api_key: str = Field(..., env="TIME_MCP_API_KEY")
    
    sequential_thinking_endpoint: str = Field(..., env="SEQ_THINKING_MCP_ENDPOINT")
    sequential_thinking_api_key: str = Field(..., env="SEQ_THINKING_MCP_API_KEY")
    
    # Redis cache configuration
    redis_url: str = Field(..., env="REDIS_URL")
    cache_ttl_short: int = 300  # 5 minutes
    cache_ttl_medium: int = 3600  # 1 hour
    cache_ttl_long: int = 86400  # 24 hours
    
    class Config:
        env_file = ".env"

# Create config instance
config = Settings()
```

## Frontend Integration

Create a new API client in the frontend to interact with the updated backend:

```typescript
// New file: src/frontend/api/tripSageApi.ts
import { createClient } from '@supabase/supabase-js'
import type { Database } from '../../types/supabase'

export class TripSageApiClient {
  private supabase
  private baseUrl: string
  private token: string | null = null
  
  constructor(baseUrl: string, supabaseUrl: string, supabaseKey: string) {
    this.baseUrl = baseUrl
    this.supabase = createClient<Database>(supabaseUrl, supabaseKey)
  }
  
  async login(email: string, password: string) {
    const { data, error } = await this.supabase.auth.signInWithPassword({
      email,
      password
    })
    
    if (error) throw error
    
    this.token = data.session?.access_token || null
    return data.user
  }
  
  async createTrip(tripData: any) {
    const response = await fetch(`${this.baseUrl}/trips`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.token}`
      },
      body: JSON.stringify(tripData)
    })
    
    if (!response.ok) {
      throw new Error(`Failed to create trip: ${response.statusText}`)
    }
    
    return await response.json()
  }
  
  // Additional methods for interacting with the API
  // ...
  
  async searchKnowledge(query: string) {
    const response = await fetch(`${this.baseUrl}/knowledge/search?query=${encodeURIComponent(query)}`, {
      headers: {
        'Authorization': `Bearer ${this.token}`
      }
    })
    
    if (!response.ok) {
      throw new Error(`Knowledge search failed: ${response.statusText}`)
    }
    
    return await response.json()
  }
}
```

## Caching Implementation

Create a Redis-based caching system:

```python
# New file: /src/cache/redis_cache.py
import json
from typing import Any, Dict, Optional, Union
import redis.asyncio as redis
from config import config

class RedisCache:
    """Redis-based caching system for TripSage"""
    
    def __init__(self):
        self.redis = redis.from_url(config.redis_url)
        
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get a value from the cache"""
        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None
        
    async def set(self, key: str, value: Dict[str, Any], ttl: int) -> bool:
        """Set a value in the cache with a TTL"""
        return await self.redis.set(key, json.dumps(value), ex=ttl)
        
    async def delete(self, key: str) -> bool:
        """Delete a value from the cache"""
        return await self.redis.delete(key) > 0
        
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching the pattern"""
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0
```

## Environment Setup

Create a comprehensive environment file template:

```bash
# New file: .env.example

# OpenAI API (Legacy)
OPENAI_API_KEY=your-openai-api-key

# Supabase Configuration
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-key

# Memory MCP Server
MEMORY_MCP_ENDPOINT=https://memory-mcp.example.com
MEMORY_MCP_API_KEY=your-memory-mcp-api-key

# Google Maps MCP Server
GOOGLE_MAPS_MCP_ENDPOINT=https://google-maps-mcp.example.com
GOOGLE_MAPS_MCP_API_KEY=your-google-maps-mcp-api-key

# Airbnb MCP Server
AIRBNB_MCP_ENDPOINT=https://airbnb-mcp.example.com
AIRBNB_MCP_API_KEY=your-airbnb-mcp-api-key

# Time MCP Server
TIME_MCP_ENDPOINT=https://time-mcp.example.com
TIME_MCP_API_KEY=your-time-mcp-api-key

# Sequential Thinking MCP Server
SEQ_THINKING_MCP_ENDPOINT=https://seq-thinking-mcp.example.com
SEQ_THINKING_MCP_API_KEY=your-seq-thinking-mcp-api-key

# Redis Cache
REDIS_URL=redis://localhost:6379/0

# Server Configuration
PORT=8000
NODE_ENV=development
```

## Project Structure Updates

Updated project structure to support the new architecture:

```
src/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py         # Updated for MCP integration
│   ├── config.py             # Updated with new configuration
│   ├── sequential_thinking.py # New file
│   ├── tool_interface.py     # New file
│   └── travel_agent.py       # Updated to use MCP servers
├── api/
│   ├── __init__.py
│   ├── auth.py
│   ├── database.py
│   ├── main.py               # Updated with new routers
│   └── routes/
│       ├── __init__.py
│       ├── auth.py
│       ├── flights.py
│       ├── knowledge.py      # New file
│       ├── maps.py           # New file
│       ├── accommodations.py # New file
│       ├── time_management.py # New file
│       ├── trips.py
│       └── users.py
├── cache/
│   ├── __init__.py
│   └── redis_cache.py        # New file
├── memory/
│   ├── __init__.py
│   └── knowledge_graph.py    # New file
├── mcp/
│   ├── __init__.py
│   ├── airbnb_mcp.py         # New file
│   ├── google_maps_mcp.py    # New file
│   └── time_mcp.py           # New file
└── types/
    └── supabase.ts           # Updated with new tables
```

## Implementation Timeline

1. **Phase 1: Core Architecture (Week 1-2)**
   - Refactor BaseAgent class
   - Implement tool interface standardization
   - Set up knowledge graph integration
   - Update config system

2. **Phase 2: MCP Server Implementation (Week 3-4)**
   - Implement Google Maps MCP server
   - Implement Airbnb MCP server
   - Implement Time MCP server
   - Implement Sequential Thinking integration

3. **Phase 3: API Layer Updates (Week 5)**
   - Create new API routes
   - Update existing routes for MCP integration
   - Implement caching system

4. **Phase 4: Database Updates (Week 6)**
   - Create new database migrations
   - Update TypeScript types
   - Implement dual storage architecture

5. **Phase 5: Frontend Integration (Week 7-8)**
   - Create frontend API client
   - Update UI components for new capabilities
   - Implement real-time updates

6. **Phase 6: Testing and Optimization (Week 9-10)**
   - Comprehensive testing
   - Performance optimization
   - Documentation updates