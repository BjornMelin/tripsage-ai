# API Integration

This document outlines the integration strategy between the TripSage frontend, backend API, and MCP (Model Context Protocol) servers. It details the communication flow, authentication mechanisms, and data exchange patterns that enable the complete TripSage travel planning system.

## 1. System Architecture Overview

TripSage implements a distributed architecture with the following key components:

- **Next.js Frontend**: React-based user interface with TypeScript
- **FastAPI Backend**: Python-based API server
- **Supabase Database**: PostgreSQL database with real-time capabilities
- **MCP Servers**: Specialized services that provide domain-specific functionality
  - Memory MCP Server (knowledge graph)
  - Google Maps MCP Server
  - Airbnb MCP Server
  - Time MCP Server
  - Weather MCP Server
  - Flight MCP Server
  - Accommodation MCP Server

### Communication Flow

```
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│               │      │               │      │               │
│   Next.js     │◄────►│   FastAPI     │◄────►│   Supabase    │
│   Frontend    │      │   Backend     │      │   Database    │
│               │      │               │      │               │
└───────┬───────┘      └───────┬───────┘      └───────────────┘
        │                      │
        │                      │
        ▼                      ▼
┌───────────────────────────────────────────┐
│                                           │
│              MCP Servers                  │
│                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Memory   │ │ Google   │ │ Airbnb   │  │
│  │ MCP      │ │ Maps MCP │ │ MCP      │  │
│  └──────────┘ └──────────┘ └──────────┘  │
│                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Time     │ │ Weather  │ │ Flight   │  │
│  │ MCP      │ │ MCP      │ │ MCP      │  │
│  └──────────┘ └──────────┘ └──────────┘  │
│                                           │
└───────────────────────────────────────────┘
```

## 2. API Server Configuration

### FastAPI Configuration

TripSage's backend API is built using FastAPI, a modern, high-performance web framework for building APIs with Python.

```python
# src/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, flights, trips, users

app = FastAPI(
    title="TripSage API",
    description="API for TripSage travel planning system",
    version="0.1.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(trips.router)
app.include_router(flights.router)
```

### API Endpoints

The TripSage API provides the following key endpoints:

| Endpoint                | Method | Description                           |
|-------------------------|--------|---------------------------------------|
| `/auth/login`           | POST   | User authentication                   |
| `/auth/register`        | POST   | User registration                     |
| `/auth/refresh`         | POST   | Refresh JWT token                     |
| `/users/me`             | GET    | Get current user profile              |
| `/users/me`             | PATCH  | Update user profile                   |
| `/trips`                | GET    | List user trips                       |
| `/trips`                | POST   | Create a new trip                     |
| `/trips/{trip_id}`      | GET    | Get trip details                      |
| `/trips/{trip_id}`      | PATCH  | Update trip                           |
| `/trips/{trip_id}`      | DELETE | Delete trip                           |
| `/flights/search`       | POST   | Search for flights                    |
| `/flights/{flight_id}`  | GET    | Get flight details                    |

## 3. Authentication and Security

### JWT Authentication Flow

TripSage implements JWT (JSON Web Token) authentication with the following flow:

1. **Login Request**: Client submits credentials to `/auth/login`
2. **Token Generation**: Server validates credentials and generates JWT
3. **Token Storage**: Client stores JWT in secure cookie or local storage
4. **Authenticated Requests**: Client includes JWT in Authorization header
5. **Token Validation**: Server validates JWT for protected endpoints
6. **Token Refresh**: Client refreshes expiring tokens via `/auth/refresh`

### Implementation in FastAPI

```python
# src/api/auth.py
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# User model for token payload
class TokenData(BaseModel):
    username: Optional[str] = None

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    # Get user from database
    user = get_user_from_database(username=token_data.username)
    if user is None:
        raise credentials_exception
    return user
```

### Implementation in Next.js

```typescript
// lib/auth.ts
import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { jwtDecode } from 'jwt-decode';

export function useAuth() {
  const router = useRouter();
  
  const isTokenValid = () => {
    const token = localStorage.getItem('auth_token');
    if (!token) return false;
    
    try {
      const decoded = jwtDecode(token);
      return decoded.exp * 1000 > Date.now();
    } catch {
      return false;
    }
  };
  
  const getAuthHeader = () => {
    const token = localStorage.getItem('auth_token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  };
  
  useEffect(() => {
    // Redirect to login if not authenticated
    if (!isTokenValid() && 
        router.pathname !== '/login' && 
        router.pathname !== '/register') {
      router.push('/login');
    }
  }, [router.pathname]);
  
  return {
    isTokenValid,
    getAuthHeader
  };
}
```

## 4. Frontend-Backend Integration

### API Client

The Next.js frontend uses a dedicated API client to communicate with the FastAPI backend:

```typescript
// lib/api-client.ts
import axios from 'axios';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth interceptor
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If error is 401 and not a retry, attempt token refresh
    if (error.response.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Attempt to refresh token
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await apiClient.post('/auth/refresh', {
          refresh_token: refreshToken,
        });
        
        // Store new tokens
        localStorage.setItem('auth_token', response.data.access_token);
        localStorage.setItem('refresh_token', response.data.refresh_token);
        
        // Retry original request
        originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
        return apiClient(originalRequest);
      } catch (error) {
        // Refresh failed, redirect to login
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(error);
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

### API Service

React hooks for API interaction:

```typescript
// hooks/useTrips.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import type { Trip, TripCreate, TripUpdate } from '@/types';

export function useTrips() {
  const queryClient = useQueryClient();
  
  const getTrips = async (): Promise<Trip[]> => {
    const response = await apiClient.get('/trips');
    return response.data;
  };
  
  const createTrip = async (trip: TripCreate): Promise<Trip> => {
    const response = await apiClient.post('/trips', trip);
    return response.data;
  };
  
  const updateTrip = async ({ id, ...data }: TripUpdate & { id: string }): Promise<Trip> => {
    const response = await apiClient.patch(`/trips/${id}`, data);
    return response.data;
  };
  
  const deleteTrip = async (id: string): Promise<void> => {
    await apiClient.delete(`/trips/${id}`);
  };
  
  // Query for fetching trips
  const tripsQuery = useQuery({
    queryKey: ['trips'],
    queryFn: getTrips,
  });
  
  // Mutation for creating trips
  const createTripMutation = useMutation({
    mutationFn: createTrip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });
  
  // Mutation for updating trips
  const updateTripMutation = useMutation({
    mutationFn: updateTrip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });
  
  // Mutation for deleting trips
  const deleteTripMutation = useMutation({
    mutationFn: deleteTrip,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trips'] });
    },
  });
  
  return {
    trips: tripsQuery.data || [],
    isLoading: tripsQuery.isLoading,
    error: tripsQuery.error,
    createTrip: createTripMutation.mutateAsync,
    updateTrip: updateTripMutation.mutateAsync,
    deleteTrip: deleteTripMutation.mutateAsync,
  };
}
```

## 5. API-MCP Server Integration

### MCP Server Architecture

MCP servers provide specialized functionality that extends the core API. Each MCP server implements the Model Context Protocol, allowing it to expose tools and resources through a standardized interface.

#### MCP Server Components

1. **Tools**: Functions that perform actions (similar to RPC methods)
2. **Resources**: Data sources that provide information
3. **Prompts**: Templates that guide interaction

### Backend Integration with MCP Servers

The FastAPI backend interacts with MCP servers using a dedicated MCP client library:

```python
# src/api/mcp_client.py
import json
import logging
import os
import subprocess
from typing import Any, Dict, List, Optional, Union

import httpx

logger = logging.getLogger(__name__)

class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self, server_name: str, server_config: Dict[str, Any]):
        self.server_name = server_name
        self.server_config = server_config
        self.server_process = None
        
        # Initialize transport based on config
        if server_config.get("transport") == "http":
            self.transport = "http"
            self.base_url = server_config["url"]
        else:
            self.transport = "stdio"
            
    async def start_server(self) -> None:
        """Start the MCP server process if using stdio transport."""
        if self.transport != "stdio":
            return
            
        if self.server_process:
            logger.warning(f"MCP server {self.server_name} already running")
            return
            
        command = self.server_config["command"]
        args = self.server_config.get("args", [])
        env = {**os.environ, **(self.server_config.get("env") or {})}
        
        try:
            self.server_process = subprocess.Popen(
                [command, *args],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                bufsize=1,
            )
            logger.info(f"Started MCP server {self.server_name}")
        except Exception as e:
            logger.error(f"Failed to start MCP server {self.server_name}: {e}")
            raise

    async def stop_server(self) -> None:
        """Stop the MCP server process if running."""
        if self.server_process:
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None
            logger.info(f"Stopped MCP server {self.server_name}")
    
    async def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke an MCP tool."""
        if self.transport == "http":
            return await self._invoke_tool_http(tool_name, parameters)
        else:
            return await self._invoke_tool_stdio(tool_name, parameters)
    
    async def _invoke_tool_http(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool via HTTP transport."""
        async with httpx.AsyncClient() as client:
            request_data = {
                "tool": tool_name,
                "parameters": parameters
            }
            response = await client.post(
                f"{self.base_url}/tools/{tool_name}",
                json=request_data,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
    
    async def _invoke_tool_stdio(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Invoke a tool via stdio transport."""
        if not self.server_process:
            await self.start_server()
        
        request_data = {
            "type": "tool_call",
            "tool": tool_name,
            "parameters": parameters
        }
        
        self.server_process.stdin.write(json.dumps(request_data) + "\n")
        self.server_process.stdin.flush()
        
        # Read response
        response_line = self.server_process.stdout.readline()
        return json.loads(response_line)
```

### MCP Service in FastAPI

```python
# src/api/mcp_service.py
import logging
from typing import Dict, Any, Optional

from fastapi import Depends

from mcp_client import MCPClient
from config import get_mcp_config

logger = logging.getLogger(__name__)

_mcp_clients: Dict[str, MCPClient] = {}

def get_mcp_client(server_name: str) -> MCPClient:
    """Get or create an MCP client for the specified server."""
    if server_name not in _mcp_clients:
        config = get_mcp_config().get(server_name)
        if not config:
            raise ValueError(f"MCP server config not found: {server_name}")
        
        _mcp_clients[server_name] = MCPClient(server_name, config)
    
    return _mcp_clients[server_name]

async def invoke_mcp_tool(
    server_name: str, 
    tool_name: str, 
    parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """Invoke an MCP tool on the specified server."""
    client = get_mcp_client(server_name)
    try:
        result = await client.invoke_tool(tool_name, parameters)
        return result
    except Exception as e:
        logger.error(f"Error invoking MCP tool {server_name}.{tool_name}: {e}")
        raise
```

### Integration Example: Flight Search API

```python
# src/api/routes/flights.py
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth import User, get_current_active_user
from mcp_service import invoke_mcp_tool

router = APIRouter(
    prefix="/flights",
    tags=["flights"],
)

class FlightSearchParams(BaseModel):
    origin: str
    destination: str
    departure_date: str
    return_date: Optional[str] = None
    adults: int = 1
    max_results: int = 10

class Flight(BaseModel):
    id: str
    airline: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    duration: int
    price: float
    booking_link: Optional[str] = None

@router.post("/search", response_model=List[Flight])
async def search_flights(
    params: FlightSearchParams,
    current_user: User = Depends(get_current_active_user),
):
    """Search for flights using the Flight MCP Server."""
    try:
        # Convert API params to MCP tool params
        mcp_params = {
            "origin": params.origin,
            "destination": params.destination,
            "departure_date": params.departure_date,
            "return_date": params.return_date,
            "adults": params.adults,
            "max_results": params.max_results,
        }
        
        # Invoke MCP tool
        result = await invoke_mcp_tool("flights-mcp", "search_flights", mcp_params)
        
        if not result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"Flight search failed: {result.get('error')}"
            )
        
        # Transform MCP results to API response format
        flights = []
        for flight_data in result.get("flights", []):
            flights.append(Flight(
                id=flight_data["id"],
                airline=flight_data["airline"],
                flight_number=flight_data["flight_number"],
                origin=flight_data["origin"],
                destination=flight_data["destination"],
                departure_time=flight_data["departure_time"],
                arrival_time=flight_data["arrival_time"],
                duration=flight_data["duration_minutes"],
                price=flight_data["price"],
                booking_link=flight_data.get("booking_link")
            ))
        
        return flights
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching flights: {str(e)}"
        )
```

## 6. MCP Server Configuration

TripSage uses a standardized configuration for MCP servers:

```python
# src/api/config.py
import os
import yaml
from typing import Dict, Any

def get_mcp_config() -> Dict[str, Dict[str, Any]]:
    """Load MCP server configuration."""
    config_path = os.getenv("MCP_CONFIG_PATH", "config/mcp_servers.yaml")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables
    for server_name, server_config in config.items():
        env_prefix = f"MCP_{server_name.upper().replace('-', '_')}_"
        
        if env_url := os.getenv(f"{env_prefix}URL"):
            server_config["transport"] = "http"
            server_config["url"] = env_url
        
        if env_command := os.getenv(f"{env_prefix}COMMAND"):
            server_config["command"] = env_command
        
        if env_args := os.getenv(f"{env_prefix}ARGS"):
            server_config["args"] = env_args.split()
    
    return config
```

Example MCP configuration file:

```yaml
# config/mcp_servers.yaml
memory-mcp:
  transport: stdio
  command: node
  args:
    - /opt/tripsage/mcp/memory-mcp/server.js
  env:
    NEO4J_URI: neo4j://localhost:7687
    NEO4J_USER: neo4j
    NEO4J_PASSWORD: password

google-maps-mcp:
  transport: http
  url: http://localhost:3001
  env:
    GOOGLE_MAPS_API_KEY: YOUR_API_KEY

flights-mcp:
  transport: stdio
  command: python
  args:
    - /opt/tripsage/mcp/flights-mcp/server.py
  env:
    AMADEUS_API_KEY: YOUR_API_KEY
    AMADEUS_API_SECRET: YOUR_API_SECRET
```

## 7. Data Exchange and Caching

### API Response Format

TripSage API responses follow a consistent format:

```typescript
interface ApiResponse<T> {
  data?: T;
  error?: {
    message: string;
    code?: string;
    details?: any;
  };
}
```

### Data Transformation Flow

When data flows through the system, it undergoes transformation at each layer:

1. **MCP Server Response**: Raw data from external APIs
2. **Backend Transformation**: Structured for internal API consistency
3. **Frontend Transformation**: Adapted for UI presentation

Example transformation flow for flight search:

```
MCP Server (External API) → Backend API → Frontend
   Raw Flight Data       →  Flight DTO  → UI Flight Model
```

### Caching Strategy

TripSage implements a multi-level caching strategy:

1. **MCP Server Caching**: Each MCP server implements appropriate caching for its domain
   - Google Maps MCP caches geocoding results for 24 hours
   - Flight MCP caches search results for 10 minutes
   
2. **API Server Caching**: FastAPI implements in-memory caching for common queries
   - User profile data: 5 minutes TTL
   - Trip listings: 1 minute TTL
   
3. **Frontend Caching**: React Query with appropriate stale times
   - Trip data: 30 seconds stale time
   - Search results: No stale time (always fresh)

```typescript
// Frontend caching example with React Query
const { data: trips } = useQuery({
  queryKey: ['trips'],
  queryFn: getTrips,
  staleTime: 30 * 1000, // 30 seconds
  cacheTime: 5 * 60 * 1000, // 5 minutes
});
```

## 8. Error Handling and Logging

### Error Response Format

TripSage implements consistent error handling across all integration points:

```typescript
interface ErrorResponse {
  error: {
    message: string;
    code: string;
    details?: any;
  };
}
```

### Error Propagation Flow

Error handling follows this propagation flow:

1. **MCP Server Errors**: Caught and wrapped by the MCP client
2. **API Server Errors**: Transformed into structured HTTP responses
3. **Frontend Errors**: Parsed and displayed in appropriate UI components

```python
# Example error handling in API
try:
    result = await invoke_mcp_tool("flights-mcp", "search_flights", mcp_params)
    # Process result
except Exception as e:
    logger.error(f"Flight search error: {str(e)}")
    raise HTTPException(
        status_code=500,
        detail={
            "message": "Failed to search flights",
            "code": "FLIGHT_SEARCH_ERROR",
            "details": str(e)
        }
    )
```

### Logging Strategy

TripSage implements structured logging across components:

1. **Request ID**: Each request chain is assigned a unique ID
2. **Correlation ID**: Links related operations across services
3. **Context Headers**: Propagate metadata between services

```python
# Logging middleware in FastAPI
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Set up context for logging
    logging_context = contextvars.ContextVar("logging_context")
    logging_context.set({"request_id": request_id})
    
    # Process request
    response = await call_next(request)
    
    # Add request ID to response
    response.headers["X-Request-ID"] = request_id
    return response
```

## 9. Real-time Updates

TripSage supports real-time updates for collaborative trip planning:

### Supabase Realtime Subscription

The frontend subscribes to real-time updates from Supabase:

```typescript
// hooks/useRealtimeTrip.ts
import { useEffect, useState } from 'react';
import { createClientSupabaseClient } from '@/lib/supabase/client';
import type { Trip } from '@/types';

export function useRealtimeTrip(tripId: string) {
  const [trip, setTrip] = useState<Trip | null>(null);
  const [loading, setLoading] = useState(true);
  const supabase = createClientSupabaseClient();
  
  useEffect(() => {
    // Fetch initial data
    const fetchTrip = async () => {
      setLoading(true);
      const { data, error } = await supabase
        .from('trips')
        .select('*')
        .eq('id', tripId)
        .single();
      
      if (error) {
        console.error('Error fetching trip:', error);
      } else if (data) {
        setTrip(data);
      }
      
      setLoading(false);
    };
    
    fetchTrip();
    
    // Subscribe to changes
    const subscription = supabase
      .channel(`trip-${tripId}`)
      .on(
        'postgres_changes', 
        {
          event: 'UPDATE',
          schema: 'public',
          table: 'trips',
          filter: `id=eq.${tripId}`
        }, 
        payload => {
          setTrip(payload.new as Trip);
        }
      )
      .subscribe();
    
    return () => {
      supabase.removeChannel(subscription);
    };
  }, [tripId]);
  
  return { trip, loading };
}
```

### Server-Sent Events (SSE)

For updates from MCP servers, TripSage uses Server-Sent Events:

```typescript
// hooks/useFlightPriceAlerts.ts
import { useEffect, useState } from 'react';
import apiClient from '@/lib/api-client';

export function useFlightPriceAlerts(flightIds: string[]) {
  const [alerts, setAlerts] = useState<FlightPriceAlert[]>([]);
  
  useEffect(() => {
    if (!flightIds.length) return;
    
    // Create SSE connection
    const eventSource = new EventSource(
      `${apiClient.defaults.baseURL}/flights/price-alerts?ids=${flightIds.join(',')}`
    );
    
    // Handle incoming alerts
    eventSource.onmessage = (event) => {
      const alert = JSON.parse(event.data);
      setAlerts(prev => [...prev, alert]);
    };
    
    // Handle errors
    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };
    
    return () => {
      eventSource.close();
    };
  }, [flightIds]);
  
  return alerts;
}
```

## 10. Development and Testing

### Development Setup

To run the integrated system locally, use the following setup:

```bash
# Start FastAPI backend
cd src/api
uvicorn main:app --reload

# Start Next.js frontend
cd frontend
npm run dev

# Start MCP servers
cd mcp/memory-mcp
npm start

cd mcp/google-maps-mcp
npm start

# ... start other MCP servers
```

### Testing Integration Points

TripSage implements the following integration tests:

1. **API Contract Tests**: Verify API endpoints match specifications
2. **MCP Integration Tests**: Test communication with MCP servers
3. **End-to-End Tests**: Test complete user flows

```python
# Example API integration test
async def test_flight_search_api():
    # Mock MCP client
    async def mock_invoke_mcp_tool(server, tool, params):
        assert server == "flights-mcp"
        assert tool == "search_flights"
        assert params["origin"] == "LAX"
        assert params["destination"] == "JFK"
        
        return {
            "success": True,
            "flights": [
                {
                    "id": "flight1",
                    "airline": "Test Airline",
                    "flight_number": "TA123",
                    "origin": "LAX",
                    "destination": "JFK",
                    "departure_time": "2025-06-01T08:00:00Z",
                    "arrival_time": "2025-06-01T16:00:00Z",
                    "duration_minutes": 360,
                    "price": 299.99
                }
            ]
        }
    
    # Patch the MCP service
    with patch("mcp_service.invoke_mcp_tool", mock_invoke_mcp_tool):
        # Make request to API
        response = await client.post(
            "/flights/search",
            json={
                "origin": "LAX",
                "destination": "JFK",
                "departure_date": "2025-06-01"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["airline"] == "Test Airline"
        assert data[0]["price"] == 299.99
```

## Conclusion

This document outlines the comprehensive integration strategy for the TripSage application. By implementing standardized communication patterns between the Next.js frontend, FastAPI backend, and specialized MCP servers, TripSage provides a robust and scalable architecture for travel planning.

The integration leverages modern technologies and best practices, including:

- JWT authentication for secure API access
- React Query for efficient data fetching and caching
- Supabase real-time subscriptions for collaborative planning
- Server-Sent Events for push notifications
- MCP servers for specialized domain functionality

This architecture enables TripSage to deliver a responsive, data-rich travel planning experience while maintaining separation of concerns and scalable development practices.