# 🔧 Debugging Guide

> *Last updated: June 16, 2025*

This guide covers debugging techniques, tools, and troubleshooting strategies for TripSage AI development across Python backend, TypeScript frontend, and infrastructure components.

## 📋 Table of Contents

- [🔧 Debugging Guide](#-debugging-guide)
  - [📋 Table of Contents](#-table-of-contents)
  - [🐍 Python Backend Debugging](#-python-backend-debugging)
    - [**Built-in Debugger**](#built-in-debugger)
    - [**IDE Debugging (VS Code)**](#ide-debugging-vs-code)
    - [**Async Debugging**](#async-debugging)
  - [🎨 Frontend Debugging](#-frontend-debugging)
    - [**Browser DevTools**](#browser-devtools)
    - [**React DevTools**](#react-devtools)
    - [**Network Debugging**](#network-debugging)
  - [🗄️ Database Debugging](#️-database-debugging)
    - [**SQL Query Debugging**](#sql-query-debugging)
    - [**Database Connection Debugging**](#database-connection-debugging)
  - [🔄 Cache Debugging](#-cache-debugging)
    - [**DragonflyDB Debugging**](#dragonflydb-debugging)
  - [🤖 AI Agent Debugging](#-ai-agent-debugging)
    - [**LangGraph Debugging**](#langgraph-debugging)
    - [**Memory System Debugging**](#memory-system-debugging)
  - [🌐 API Integration Debugging](#-api-integration-debugging)
    - [**External API Debugging**](#external-api-debugging)
  - [📊 Performance Debugging](#-performance-debugging)
    - [**Profiling Tools**](#profiling-tools)
  - [🔍 Logging \& Monitoring](#-logging--monitoring)
    - [**Structured Logging**](#structured-logging)
  - [🚨 Common Issues](#-common-issues)
    - [**Database Issues**](#database-issues)
    - [**API Issues**](#api-issues)
  - [🛠️ Development Tools](#️-development-tools)
    - [**Custom Debug Middleware**](#custom-debug-middleware)
  - [📚 Debugging Workflows](#-debugging-workflows)
    - [**Systematic Debugging Process**](#systematic-debugging-process)

## 🐍 Python Backend Debugging

### **Built-in Debugger**

```python
# Using pdb for interactive debugging
import pdb

async def process_trip_request(trip_data: dict):
    """Process trip request with debugging."""
    pdb.set_trace()  # Breakpoint here
    
    # Debug variables
    print(f"Trip data: {trip_data}")
    
    # Step through logic
    validated_data = validate_trip_data(trip_data)
    trip = await create_trip(validated_data)
    
    return trip

# Using breakpoint() (Python 3.7+)
async def search_flights(params: FlightSearchParams):
    """Search flights with debugging."""
    breakpoint()  # Modern breakpoint
    
    # Debug API call
    response = await duffel_client.search(params)
    return response
```

### **IDE Debugging (VS Code)**

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Debug FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/tripsage/api/main.py",
            "console": "integratedTerminal",
            "env": {
                "ENVIRONMENT": "development",
                "DEBUG": "true"
            },
            "args": ["--reload", "--port", "8001"]
        },
        {
            "name": "Debug Tests",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "${workspaceFolder}/tests",
                "-v",
                "--tb=short"
            ],
            "console": "integratedTerminal"
        }
    ]
}
```

### **Async Debugging**

```python
import asyncio
import logging

# Debug async operations
async def debug_async_operation():
    """Debug async operations with proper logging."""
    logger = logging.getLogger(__name__)
    
    try:
        # Log start
        logger.debug("Starting async operation")
        
        # Debug concurrent operations
        tasks = [
            search_flights_async(params1),
            search_hotels_async(params2),
            get_weather_async(location)
        ]
        
        # Debug task completion
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.exception(f"Task {i} failed: {result}")
            else:
                logger.debug(f"Task {i} completed: {type(result)}")
        
        return results
        
    except Exception as e:
        logger.exception("Async operation failed")
        raise

# Debug database sessions
async def debug_database_operation(db: AsyncSession):
    """Debug database operations."""
    try:
        # Enable SQL logging
        logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
        
        # Debug query
        query = select(TripModel).where(TripModel.user_id == user_id)
        result = await db.execute(query)
        
        # Log result
        trips = result.scalars().all()
        logger.debug(f"Found {len(trips)} trips")
        
        return trips
        
    except Exception as e:
        logger.exception("Database operation failed")
        await db.rollback()
        raise
```

## 🎨 Frontend Debugging

### **Browser DevTools**

```typescript
// Debug React components
import { useEffect } from 'react';

export const TripPlanningComponent = ({ tripId }: { tripId: string }) => {
  useEffect(() => {
    // Debug component lifecycle
    console.log('TripPlanningComponent mounted', { tripId });
    
    return () => {
      console.log('TripPlanningComponent unmounted', { tripId });
    };
  }, [tripId]);

  const handleSubmit = async (data: TripData) => {
    try {
      // Debug form submission
      console.group('Trip submission');
      console.log('Form data:', data);
      console.time('API call');
      
      const result = await createTrip(data);
      
      console.timeEnd('API call');
      console.log('API response:', result);
      console.groupEnd();
      
    } catch (error) {
      console.error('Trip creation failed:', error);
      
      // Debug error details
      if (error instanceof Error) {
        console.error('Error message:', error.message);
        console.error('Error stack:', error.stack);
      }
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Component JSX */}
    </form>
  );
};
```

### **React DevTools**

```typescript
// Debug state management with Zustand
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

interface TripStore {
  trips: Trip[];
  loading: boolean;
  error: string | null;
  fetchTrips: () => Promise<void>;
}

export const useTripStore = create<TripStore>()(
  devtools(
    (set, get) => ({
      trips: [],
      loading: false,
      error: null,
      
      fetchTrips: async () => {
        set({ loading: true, error: null });
        
        try {
          const trips = await api.getTrips();
          set({ trips, loading: false });
        } catch (error) {
          set({ 
            error: error instanceof Error ? error.message : 'Unknown error',
            loading: false 
          });
        }
      },
    }),
    {
      name: 'trip-store', // DevTools name
    }
  )
);

// Debug custom hooks
import { useDebugValue } from 'react';

export const useTrip = (tripId: string) => {
  const trip = useTripStore(state => 
    state.trips.find(t => t.id === tripId)
  );
  
  // Show in React DevTools
  useDebugValue(trip ? `Trip: ${trip.name}` : 'No trip');
  
  return trip;
};
```

### **Network Debugging**

```typescript
// Debug API calls with interceptors
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', {
      method: config.method?.toUpperCase(),
      url: config.url,
      data: config.data,
      headers: config.headers,
    });
    return config;
  },
  (error) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', {
      status: response.status,
      data: response.data,
      headers: response.headers,
    });
    return response;
  },
  (error) => {
    console.error('Response Error:', {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message,
    });
    return Promise.reject(error);
  }
);
```

## 🗄️ Database Debugging

### **SQL Query Debugging**

```python
# Enable SQL logging
import logging

# Configure SQLAlchemy logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
logging.getLogger("sqlalchemy.pool").setLevel(logging.DEBUG)

# Debug specific queries
from sqlalchemy import text

async def debug_complex_query(db: AsyncSession):
    """Debug complex database queries."""
    
    # Raw SQL for debugging
    raw_query = text("""
        SELECT t.*, COUNT(d.id) as destination_count
        FROM trips t
        LEFT JOIN destinations d ON t.id = d.trip_id
        WHERE t.user_id = :user_id
        GROUP BY t.id
        ORDER BY t.created_at DESC
    """)
    
    result = await db.execute(raw_query, {"user_id": user_id})
    
    # Debug result
    rows = result.fetchall()
    for row in rows:
        print(f"Trip: {row.name}, Destinations: {row.destination_count}")
    
    return rows

# Debug ORM queries
async def debug_orm_query(db: AsyncSession):
    """Debug ORM queries with explain."""
    
    query = (
        select(TripModel)
        .options(joinedload(TripModel.destinations))
        .where(TripModel.user_id == user_id)
    )
    
    # Get query string for debugging
    compiled = query.compile(compile_kwargs={"literal_binds": True})
    print(f"Generated SQL: {compiled}")
    
    # Execute with timing
    import time
    start_time = time.time()
    result = await db.execute(query)
    execution_time = time.time() - start_time
    
    print(f"Query executed in {execution_time:.3f}s")
    
    return result.scalars().all()
```

### **Database Connection Debugging**

```python
# Debug connection pool
from sqlalchemy.pool import StaticPool

async def debug_database_connections():
    """Debug database connection issues."""
    
    # Check connection pool status
    engine = get_database_engine()
    pool = engine.pool
    
    print(f"Pool size: {pool.size()}")
    print(f"Checked out connections: {pool.checkedout()}")
    print(f"Overflow: {pool.overflow()}")
    print(f"Invalid connections: {pool.invalidated()}")
    
    # Test connection
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print(f"Connection test: {result.scalar()}")
    except Exception as e:
        print(f"Connection failed: {e}")

# Debug transaction issues
async def debug_transaction(db: AsyncSession):
    """Debug transaction problems."""
    
    try:
        # Start transaction
        print("Starting transaction")
        
        # Perform operations
        trip = TripModel(name="Test Trip")
        db.add(trip)
        
        # Check transaction state
        print(f"Transaction active: {db.in_transaction()}")
        print(f"Dirty objects: {len(db.dirty)}")
        print(f"New objects: {len(db.new)}")
        
        await db.commit()
        print("Transaction committed")
        
    except Exception as e:
        print(f"Transaction failed: {e}")
        await db.rollback()
        print("Transaction rolled back")
```

## 🔄 Cache Debugging

### **DragonflyDB Debugging**

```python
# Debug cache operations
import json
from tripsage_core.services.infrastructure.cache_service import CacheService

async def debug_cache_operations():
    """Debug cache operations."""
    
    cache = CacheService()
    
    # Test cache connectivity
    try:
        await cache.ping()
        print("Cache connection: OK")
    except Exception as e:
        print(f"Cache connection failed: {e}")
        return
    
    # Debug cache operations
    test_key = "debug:test"
    test_value = {"message": "Hello, Cache!"}
    
    # Set value
    await cache.set(test_key, test_value, ttl=60)
    print(f"Set cache key: {test_key}")
    
    # Get value
    cached_value = await cache.get(test_key)
    print(f"Retrieved value: {cached_value}")
    
    # Check TTL
    ttl = await cache.ttl(test_key)
    print(f"TTL: {ttl} seconds")
    
    # List keys
    keys = await cache.keys("debug:*")
    print(f"Debug keys: {keys}")

# Debug cache performance
async def debug_cache_performance():
    """Debug cache performance issues."""
    
    import time
    cache = CacheService()
    
    # Test cache latency
    start_time = time.time()
    await cache.get("nonexistent:key")
    latency = time.time() - start_time
    print(f"Cache latency: {latency:.3f}s")
    
    # Test cache hit/miss
    cache_key = "performance:test"
    
    # Miss
    start_time = time.time()
    result = await cache.get(cache_key)
    miss_time = time.time() - start_time
    print(f"Cache miss time: {miss_time:.3f}s")
    
    # Set
    await cache.set(cache_key, {"data": "test"})
    
    # Hit
    start_time = time.time()
    result = await cache.get(cache_key)
    hit_time = time.time() - start_time
    print(f"Cache hit time: {hit_time:.3f}s")
```

## 🤖 AI Agent Debugging

### **LangGraph Debugging**

```python
# Debug LangGraph workflows
from langgraph.graph import StateGraph
import logging

# Enable LangGraph debugging
logging.getLogger("langgraph").setLevel(logging.DEBUG)

async def debug_agent_workflow(trip_id: str, user_message: str):
    """Debug AI agent workflow execution."""
    
    # Create debug state
    initial_state = {
        "trip_id": trip_id,
        "user_message": user_message,
        "debug_info": [],
        "step_count": 0
    }
    
    # Debug each step
    def debug_step(step_name: str):
        def decorator(func):
            async def wrapper(state):
                print(f"\n=== Step: {step_name} ===")
                print(f"Input state: {state}")
                
                try:
                    result = await func(state)
                    print(f"Output state: {result}")
                    
                    # Add debug info
                    result["debug_info"].append({
                        "step": step_name,
                        "status": "success",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    return result
                    
                except Exception as e:
                    print(f"Step failed: {e}")
                    state["debug_info"].append({
                        "step": step_name,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    raise
            
            return wrapper
        return decorator
    
    # Apply debug decorator to agent steps
    @debug_step("analyze_request")
    async def analyze_request(state):
        # Analyze user request
        analysis = await analyze_user_message(state["user_message"])
        state["analysis"] = analysis
        return state
    
    @debug_step("search_flights")
    async def search_flights(state):
        # Search for flights
        if state["analysis"]["intent"] == "search_flights":
            flights = await search_flights_for_trip(state["trip_id"])
            state["flights"] = flights
        return state
    
    # Execute workflow with debugging
    workflow = StateGraph()
    workflow.add_node("analyze", analyze_request)
    workflow.add_node("search", search_flights)
    workflow.add_edge("analyze", "search")
    
    result = await workflow.ainvoke(initial_state)
    
    # Print debug summary
    print("\n=== Debug Summary ===")
    for debug_entry in result["debug_info"]:
        print(f"{debug_entry['step']}: {debug_entry['status']}")
    
    return result
```

### **Memory System Debugging**

```python
# Debug Mem0 memory operations
from mem0 import Memory

async def debug_memory_operations(user_id: str):
    """Debug memory system operations."""
    
    memory = Memory()
    
    # Debug memory search
    query = "flights to Paris"
    memories = memory.search(query, user_id=user_id)
    
    print(f"Memory search for '{query}':")
    for i, mem in enumerate(memories):
        print(f"  {i+1}. {mem['memory']} (score: {mem['score']:.3f})")
    
    # Debug memory addition
    new_memory = "User prefers morning flights"
    result = memory.add(new_memory, user_id=user_id)
    print(f"Added memory: {result}")
    
    # Debug memory retrieval
    all_memories = memory.get_all(user_id=user_id)
    print(f"Total memories for user: {len(all_memories)}")
    
    return memories
```

## 🌐 API Integration Debugging

### **External API Debugging**

```python
# Debug external API calls
import httpx
import json

async def debug_external_api_call():
    """Debug external API integration."""
    
    async with httpx.AsyncClient() as client:
        try:
            # Debug request
            url = "https://api.duffel.com/air/offers"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "data": {
                    "slices": [
                        {
                            "origin": "LHR",
                            "destination": "JFK",
                            "departure_date": "2025-07-01"
                        }
                    ],
                    "passengers": [{"type": "adult"}]
                }
            }
            
            print(f"Request URL: {url}")
            print(f"Request headers: {headers}")
            print(f"Request payload: {json.dumps(payload, indent=2)}")
            
            # Make request with timeout
            response = await client.post(
                url,
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response data: {json.dumps(data, indent=2)}")
                return data
            else:
                print(f"Error response: {response.text}")
                response.raise_for_status()
                
        except httpx.TimeoutException:
            print("Request timed out")
        except httpx.RequestError as e:
            print(f"Request error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

# Debug rate limiting
class DebugRateLimiter:
    def __init__(self):
        self.requests = []
    
    async def make_request(self, func, *args, **kwargs):
        """Make request with rate limiting debug."""
        
        import time
        now = time.time()
        
        # Clean old requests
        self.requests = [req for req in self.requests if now - req < 60]
        
        print(f"Requests in last minute: {len(self.requests)}")
        
        if len(self.requests) >= 100:  # Rate limit
            wait_time = 60 - (now - self.requests[0])
            print(f"Rate limited. Wait {wait_time:.1f}s")
            await asyncio.sleep(wait_time)
        
        # Make request
        self.requests.append(now)
        return await func(*args, **kwargs)
```

## 📊 Performance Debugging

### **Profiling Tools**

```python
# Profile function performance
import cProfile
import pstats
from functools import wraps

def profile_function(func):
    """Decorator to profile function performance."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            profiler.disable()
            
            # Print stats
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(10)  # Top 10 functions
    
    return wrapper

# Memory profiling
import tracemalloc

async def debug_memory_usage():
    """Debug memory usage patterns."""
    
    # Start tracing
    tracemalloc.start()
    
    # Perform operations
    trips = await load_large_dataset()
    
    # Get memory snapshot
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    print("Top 10 memory allocations:")
    for stat in top_stats[:10]:
        print(f"{stat.traceback.format()[-1]}: {stat.size / 1024:.1f} KB")
    
    tracemalloc.stop()

# Database query performance
async def debug_query_performance(db: AsyncSession):
    """Debug database query performance."""
    
    import time
    
    # Test query performance
    queries = [
        select(TripModel).where(TripModel.user_id == user_id),
        select(TripModel).options(joinedload(TripModel.destinations)),
        select(TripModel).options(selectinload(TripModel.flights))
    ]
    
    for i, query in enumerate(queries):
        start_time = time.time()
        result = await db.execute(query)
        execution_time = time.time() - start_time
        
        rows = result.scalars().all()
        print(f"Query {i+1}: {execution_time:.3f}s ({len(rows)} rows)")
```

## 🔍 Logging & Monitoring

### **Structured Logging**

```python
# Configure structured logging
import logging
import json
from datetime import datetime

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
    
    def log_event(self, level: str, event: str, **kwargs):
        """Log structured event."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "level": level,
            **kwargs
        }
        
        getattr(self.logger, level.lower())(json.dumps(log_data))
    
    def log_api_request(self, method: str, url: str, status: int, duration: float):
        """Log API request."""
        self.log_event(
            "info",
            "api_request",
            method=method,
            url=url,
            status_code=status,
            duration_ms=duration * 1000
        )
    
    def log_error(self, error: Exception, context: dict = None):
        """Log error with context."""
        self.log_event(
            "error",
            "error_occurred",
            error_type=type(error).__name__,
            error_message=str(error),
            context=context or {}
        )

# Usage
logger = StructuredLogger("tripsage.api")

async def example_function():
    try:
        # Log start
        logger.log_event("info", "function_start", function="example_function")
        
        # Perform operation
        result = await some_operation()
        
        # Log success
        logger.log_event("info", "function_success", result_count=len(result))
        
    except Exception as e:
        # Log error
        logger.log_error(e, {"function": "example_function"})
        raise
```

## 🚨 Common Issues

### **Database Issues**

```python
# Common database debugging scenarios

# 1. Connection pool exhaustion
async def debug_connection_pool():
    """Debug connection pool issues."""
    
    # Check pool status
    engine = get_database_engine()
    print(f"Pool size: {engine.pool.size()}")
    print(f"Checked out: {engine.pool.checkedout()}")
    
    # Solution: Ensure proper session cleanup
    async with AsyncSession(engine) as session:
        try:
            # Use session
            result = await session.execute(query)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        # Session automatically closed

# 2. Deadlock detection
async def debug_deadlocks(db: AsyncSession):
    """Debug database deadlocks."""
    
    try:
        # Use consistent lock ordering
        async with db.begin():
            # Lock resources in consistent order
            trip = await db.get(TripModel, trip_id, with_for_update=True)
            user = await db.get(UserModel, user_id, with_for_update=True)
            
            # Perform operations
            trip.status = "confirmed"
            user.last_activity = datetime.utcnow()
            
    except Exception as e:
        if "deadlock" in str(e).lower():
            print("Deadlock detected - retrying...")
            await asyncio.sleep(0.1)  # Brief delay
            return await debug_deadlocks(db)  # Retry
        raise

# 3. Slow queries
async def debug_slow_queries():
    """Debug slow database queries."""
    
    # Enable query logging
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    
    # Use EXPLAIN for query analysis
    query = text("""
        EXPLAIN ANALYZE
        SELECT t.*, COUNT(d.id) as dest_count
        FROM trips t
        LEFT JOIN destinations d ON t.id = d.trip_id
        WHERE t.user_id = :user_id
        GROUP BY t.id
    """)
    
    result = await db.execute(query, {"user_id": user_id})
    for row in result:
        print(row[0])  # EXPLAIN output
```

### **API Issues**

```python
# Common API debugging scenarios

# 1. Authentication issues
async def debug_auth_issues(request: Request):
    """Debug authentication problems."""
    
    # Check headers
    auth_header = request.headers.get("Authorization")
    print(f"Auth header: {auth_header}")
    
    if not auth_header:
        print("Missing Authorization header")
        return
    
    try:
        token = auth_header.split(" ")[1]
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        print(f"Token payload: {payload}")
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.utcnow():
            print("Token expired")
        
    except jwt.InvalidTokenError as e:
        print(f"Invalid token: {e}")

# 2. CORS issues
def debug_cors_issues():
    """Debug CORS configuration."""
    
    print("CORS configuration:")
    print(f"Allowed origins: {settings.cors_origins}")
    print(f"Allow credentials: {settings.cors_allow_credentials}")
    
    # Check preflight requests
    @app.options("/{path:path}")
    async def debug_preflight(request: Request):
        origin = request.headers.get("origin")
        method = request.headers.get("access-control-request-method")
        
        print(f"Preflight request from {origin} for {method}")
        
        return Response(
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE",
                "Access-Control-Allow-Headers": "Authorization, Content-Type",
            }
        )

# 3. Rate limiting issues
class DebugRateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
    
    def check_rate_limit(self, identifier: str) -> bool:
        """Debug rate limiting."""
        
        now = time.time()
        window = 60  # 1 minute
        limit = 100
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < window
        ]
        
        current_count = len(self.requests[identifier])
        print(f"Rate limit check for {identifier}: {current_count}/{limit}")
        
        if current_count >= limit:
            oldest_request = min(self.requests[identifier])
            reset_time = oldest_request + window
            print(f"Rate limited. Reset at {datetime.fromtimestamp(reset_time)}")
            return False
        
        self.requests[identifier].append(now)
        return True
```

## 🛠️ Development Tools

### **Custom Debug Middleware**

```python
# Debug middleware for development
@app.middleware("http")
async def debug_middleware(request: Request, call_next):
    """Debug middleware for development environment."""
    
    if not settings.debug:
        return await call_next(request)
    
    start_time = time.time()
    
    # Log request details
    print(f"\n{'='*50}")
    print(f"Request: {request.method} {request.url}")
    print(f"Headers: {dict(request.headers)}")
    
    # Log request body for POST/PUT
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()
        if body:
            try:
                json_body = json.loads(body)
                print(f"Body: {json.dumps(json_body, indent=2)}")
            except json.JSONDecodeError:
                print(f"Body (raw): {body.decode()}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        print(f"Response: {response.status_code}")
        print(f"Process time: {process_time:.3f}s")
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        print(f"Error: {e}")
        print(f"Process time: {process_time:.3f}s")
        print(f"{'='*50}\n")
        raise

# Debug endpoint for development
@app.get("/debug/info")
async def debug_info():
    """Debug endpoint with system information."""
    
    if not settings.debug:
        raise HTTPException(status_code=404)
    
    import psutil
    import sys
    
    return {
        "environment": settings.environment,
        "python_version": sys.version,
        "memory_usage": psutil.virtual_memory()._asdict(),
        "cpu_usage": psutil.cpu_percent(),
        "database_url": settings.database_url.split("@")[-1],  # Hide credentials
        "cache_url": settings.redis_url.split("@")[-1],
        "debug_mode": settings.debug,
    }
```

## 📚 Debugging Workflows

### **Systematic Debugging Process**

```python
# Debugging workflow template
class DebugWorkflow:
    def __init__(self, issue_description: str):
        self.issue = issue_description
        self.steps = []
        self.findings = []
    
    def step(self, description: str):
        """Add debugging step."""
        print(f"\n🔍 Step {len(self.steps) + 1}: {description}")
        self.steps.append(description)
    
    def finding(self, observation: str):
        """Record finding."""
        print(f"   ✓ Finding: {observation}")
        self.findings.append(observation)
    
    def reproduce_issue(self):
        """Step 1: Reproduce the issue."""
        self.step("Reproduce the issue")
        # Add reproduction steps
    
    def check_logs(self):
        """Step 2: Check logs."""
        self.step("Check application logs")
        # Check various log sources
    
    def isolate_component(self):
        """Step 3: Isolate the component."""
        self.step("Isolate the failing component")
        # Test individual components
    
    def test_hypothesis(self, hypothesis: str):
        """Step 4: Test hypothesis."""
        self.step(f"Test hypothesis: {hypothesis}")
        # Test specific hypothesis
    
    def implement_fix(self, fix_description: str):
        """Step 5: Implement fix."""
        self.step(f"Implement fix: {fix_description}")
        # Apply fix
    
    def verify_fix(self):
        """Step 6: Verify fix."""
        self.step("Verify fix resolves the issue")
        # Verify resolution

# Example usage
async def debug_trip_creation_issue():
    """Debug trip creation failure."""
    
    workflow = DebugWorkflow("Trip creation fails with 500 error")
    
    # Step 1: Reproduce
    workflow.reproduce_issue()
    try:
        trip_data = {"name": "Test Trip", "start_date": "2025-07-01"}
        result = await create_trip(trip_data)
        workflow.finding("Issue not reproduced - creation succeeded")
    except Exception as e:
        workflow.finding(f"Issue reproduced: {e}")
    
    # Step 2: Check logs
    workflow.check_logs()
    # Check application logs for errors
    
    # Step 3: Isolate component
    workflow.isolate_component()
    # Test database connection, validation, etc.
    
    # Continue with remaining steps...
```

---

This debugging guide provides comprehensive tools and techniques for troubleshooting TripSage AI development issues. Use these patterns to systematically identify and resolve problems across the entire stack.
