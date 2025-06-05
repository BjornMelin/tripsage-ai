# TripSage Application Layer Architecture

This document provides a comprehensive architectural overview of the `tripsage` package, the main application layer that builds upon `tripsage_core` to deliver travel planning functionality through APIs and agent interfaces.

## Core Principles

`tripsage` is designed as the **application layer** that:
- **Depends on** `tripsage_core` for all business logic
- Provides FastAPI web application and agent orchestration
- Handles HTTP concerns, routing, and middleware
- Integrates MCP (Model Context Protocol) servers and AI agents
- Manages real-time communication and tool orchestration

## Package Structure

```
tripsage/
├── api/                      # FastAPI application
│   ├── core/                # API configuration
│   ├── main.py             # Application entry point
│   ├── middlewares/        # HTTP middleware
│   ├── routers/            # API endpoints
│   ├── schemas/            # API request/response models
│   └── services/           # API-specific service adapters
│
├── agents/                   # AI agent implementations
│   ├── base.py             # Base agent class
│   ├── service_registry.py # Agent dependency injection
│   ├── handoffs/           # Agent coordination
│   └── *.py                # Specialized agents
│
├── mcp_abstraction/         # MCP server integration
│   ├── manager.py          # MCP manager
│   ├── registry.py         # MCP service registry
│   ├── key_mcp_integration.py  # BYOK integration
│   └── wrappers/           # MCP service wrappers
│
├── models/                  # Application-specific models
│   ├── mcp.py              # MCP base models
│   ├── accommodation.py    # MCP accommodation models
│   ├── flight.py           # MCP flight models
│   ├── memory.py           # MCP memory models
│   └── attachments.py      # File attachment models
│
├── orchestration/          # LangGraph orchestration
│   ├── graph.py           # Main orchestration graph
│   ├── nodes/             # Graph nodes
│   ├── state.py           # Graph state management
│   ├── routing.py         # Routing logic
│   └── tools/             # LangGraph tool adapters
│
├── tools/                  # Agent tools
│   ├── accommodations_tools.py
│   ├── memory_tools.py
│   ├── planning_tools.py
│   ├── web_tools.py
│   └── webcrawl/          # Web crawling infrastructure
│
├── config/                 # Application configuration
│   ├── feature_flags.py   # Feature toggles
│   └── service_registry.py # Service configuration
│
├── security/               # Security utilities
│   └── memory_security.py  # Memory access control
│
├── utils/                  # Application utilities
│   └── cache.py           # Application-level caching
│
└── db/                     # Database migrations
    └── migrations/         # Migration scripts
```

## Layer Architecture

### 1. API Layer (`api/`)

#### Core Configuration (`api/core/`)
- **config.py**: FastAPI settings and environment config
- **dependencies.py**: Dependency injection for routes
- **openapi.py**: OpenAPI schema customization

#### Routers (`api/routers/`)
**Purpose**: HTTP endpoint definitions

**Key Routers**:
- **auth.py**: Authentication endpoints
- **trips.py**: Trip management
- **flights.py**: Flight search/booking
- **accommodations.py**: Hotel search/booking
- **chat.py**: Chat interactions
- **memory.py**: Memory management
- **websocket.py**: Real-time communication
- **keys.py**: API key management

**Router Pattern**:
```python
router = APIRouter(prefix="/trips", tags=["trips"])

@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,
    trip_service: TripService = Depends(get_trip_service)
) -> TripResponse:
    trip = await trip_service.get_trip(trip_id)
    return TripResponse.from_domain(trip)
```

#### Middleware (`api/middlewares/`)
**Purpose**: Cross-cutting HTTP concerns

**Key Middleware**:
- **authentication.py**: JWT/API key validation
- **rate_limiting.py**: Request throttling
- **logging.py**: Request/response logging

#### Service Adapters (`api/services/`)
**Purpose**: Thin adapters between API and core services

**Adapter Pattern**:
```python
class AuthService:
    """API adapter for core auth service"""
    
    def __init__(self, core_service: CoreAuthService):
        self.core = core_service
    
    async def login(self, request: LoginRequest) -> AuthResponse:
        # Convert API model to domain model
        domain_user = await self.core.authenticate(
            email=request.email,
            password=request.password
        )
        # Convert domain model to API response
        return AuthResponse.from_domain(domain_user)
```

### 2. Agent Layer (`agents/`)

#### Base Agent Architecture
```python
class BaseAgent:
    """Foundation for all agents"""
    
    def __init__(self, service_registry: ServiceRegistry):
        self.services = service_registry
        self.tools = self._register_tools()
    
    @abstractmethod
    async def process(self, input: AgentInput) -> AgentOutput:
        """Process agent request"""
```

#### Specialized Agents
- **TravelAgent**: Main travel planning orchestrator
- **FlightAgent**: Flight search and booking specialist
- **AccommodationAgent**: Hotel/lodging specialist
- **DestinationResearchAgent**: Destination insights
- **BudgetAgent**: Budget optimization
- **ItineraryAgent**: Itinerary planning

#### Agent Handoffs (`agents/handoffs/`)
**Purpose**: Coordinate agent collaboration
```python
class HandoffCoordinator:
    async def handoff(
        self,
        from_agent: str,
        to_agent: str,
        context: HandoffContext
    ) -> HandoffResult:
        """Coordinate handoff between agents"""
```

### 3. MCP Abstraction Layer (`mcp_abstraction/`)

#### MCP Manager
**Purpose**: Centralized MCP server management
```python
class MCPManager:
    async def invoke(
        self,
        server: str,
        method: str,
        params: dict,
        user_key: Optional[str] = None
    ) -> Any:
        """Invoke MCP server method"""
```

#### Service Wrappers
- **AirbnbMCPWrapper**: Airbnb search integration
- Additional MCP wrappers as needed

### 4. Orchestration Layer (`orchestration/`)

#### LangGraph Integration
**Purpose**: Complex workflow orchestration

**Key Components**:
- **Graph Definition**: Workflow structure
- **State Management**: Conversation and planning state
- **Nodes**: Individual processing steps
- **Routing**: Dynamic flow control

**Graph Pattern**:
```python
workflow = StateGraph(PlanningState)

# Add nodes
workflow.add_node("research", destination_research_node)
workflow.add_node("flights", flight_search_node)
workflow.add_node("hotels", hotel_search_node)

# Add edges
workflow.add_edge("research", "flights")
workflow.add_conditional_edges(
    "flights",
    should_search_hotels,
    {True: "hotels", False: END}
)
```

### 5. Tools Layer (`tools/`)

#### Tool Categories
- **Search Tools**: Flight, hotel, destination search
- **Memory Tools**: Context storage and retrieval
- **Planning Tools**: Itinerary creation and optimization
- **Web Tools**: Web search and crawling

**Tool Pattern**:
```python
@function_tool
async def search_flights_tool(
    origin: str,
    destination: str,
    date: str,
    service_registry: ServiceRegistry
) -> FlightSearchResults:
    """Search for flights"""
    flight_service = service_registry.get_service(FlightService)
    return await flight_service.search(origin, destination, date)
```

## Integration Architecture

### Service Registry Pattern
```python
class ServiceRegistry:
    """Central service management for agents"""
    
    def __init__(self, settings: BaseAppSettings):
        self.settings = settings
        self._services = {}
        self._initialize_core_services()
    
    def get_service(self, service_type: Type[T]) -> T:
        """Get or create service instance"""
        if service_type not in self._services:
            self._services[service_type] = service_type(self.settings)
        return self._services[service_type]
```

### Dual Consumer Support

#### Frontend Consumer
- Clean REST APIs with OpenAPI docs
- WebSocket for real-time updates
- User-friendly error messages
- UI hints in responses

#### Agent Consumer
- Structured data responses
- Technical error details
- Tool suggestions
- Performance metrics

## Key Boundaries

### What tripsage DOES:
- ✅ Provides FastAPI web application
- ✅ Implements AI agents and orchestration
- ✅ Manages HTTP routing and middleware
- ✅ Integrates MCP servers
- ✅ Handles WebSocket communication
- ✅ Coordinates agent workflows

### What tripsage DOES NOT:
- ❌ Implement business logic (uses tripsage_core)
- ❌ Direct database access (uses tripsage_core)
- ❌ External API integration (uses tripsage_core)
- ❌ Define domain models (uses tripsage_core)

## Data Flow

### API Request Flow
```
Client Request
    ↓
API Router
    ↓
Middleware Stack
    ↓
Service Adapter
    ↓
Core Service (tripsage_core)
    ↓
Response Formatting
    ↓
Client Response
```

### Agent Processing Flow
```
User Query
    ↓
Agent Selection
    ↓
Tool Execution
    ↓
Core Services (tripsage_core)
    ↓
Result Processing
    ↓
Response Generation
```

## Deployment Architecture

### Application Structure
```python
# main.py
app = FastAPI(title="TripSage API")

# Add middleware
app.add_middleware(CORSMiddleware, ...)
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(RateLimitingMiddleware)

# Include routers
app.include_router(auth_router)
app.include_router(trips_router)
app.include_router(flights_router)
# ... etc

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
```

### Environment Configuration
- Development: Local with hot reload
- Staging: Containerized with limited resources
- Production: Auto-scaling with monitoring

## Testing Strategy

### Unit Testing
- Test routers with mocked services
- Test agents with mocked tools
- Test middleware in isolation

### Integration Testing
- Test API endpoints end-to-end
- Test agent workflows
- Test WebSocket communication

### Performance Testing
- Load testing for API endpoints
- Concurrent user testing
- WebSocket connection limits

## Security Considerations

### API Security
- JWT authentication for users
- API key authentication for services
- Rate limiting per consumer type
- Input validation at API boundaries

### Agent Security
- Tool execution sandboxing
- Memory access control
- Audit logging for agent actions

## Extension Points

### Adding New Endpoints
1. Create router in `api/routers/`
2. Define request/response schemas
3. Add service adapter if needed
4. Include router in main app

### Adding New Agents
1. Create agent class extending `BaseAgent`
2. Define agent tools
3. Register in service registry
4. Add to orchestration graph if needed

### Adding New Tools
1. Create tool function with `@function_tool`
2. Define tool parameters with Pydantic
3. Register in appropriate agent
4. Add to tool documentation

## Performance Optimization

### Caching Strategy
- Response caching for common queries
- Tool result caching
- WebSocket message batching

### Async Processing
- Concurrent tool execution
- Async service calls
- Background task processing

### Resource Management
- Connection pooling (via tripsage_core)
- Request throttling
- Memory limits for agents