# TripSage AI Platform Architecture Overview

This document provides a comprehensive architectural overview of the TripSage AI travel planning platform, explaining how all components work together to deliver an intelligent, unified travel planning experience.

## Table of Contents

- [Platform Overview](#platform-overview)
- [System Architecture](#system-architecture)
- [Component Overview](#component-overview)
- [Data Flow Architecture](#data-flow-architecture)
- [Integration Architecture](#integration-architecture)
- [Deployment Architecture](#deployment-architecture)
- [Performance Architecture](#performance-architecture)
- [Security Architecture](#security-architecture)

## Platform Overview

TripSage is an AI-powered travel planning platform that combines modern web technologies with advanced AI agents to provide intelligent, personalized travel planning experiences. The platform is built with a unified architecture that serves both human users through a web interface and AI agents through direct API integration.

### Current Implementation Status (June 6, 2025)

**Grade A Frontend Implementation**: 
- ✅ 70-75% complete with React 19 + Next.js 15 foundation
- ✅ Advanced agent monitoring, authentication UI, and WebSocket infrastructure ready
- ✅ Modern component architecture with shadcn-ui and comprehensive testing

**Backend Integration Status**:
- ✅ 92% complete with unified FastAPI architecture and direct SDK integrations
- ✅ **JWT Security Hardening**: Critical security vulnerability resolved - hardcoded fallback secrets removed
- ✅ **Frontend Authentication Foundation**: JWT middleware and server actions implemented with production security
- 🔄 Authentication integration gap: Frontend JWT system requires backend FastAPI service connection
- 🔄 Missing backend routers: activities.py and search.py endpoints needed

### Core Principles

1. **Unified Interface** - Single API serving multiple consumer types
2. **AI-First Design** - Built for intelligent automation and human collaboration
3. **Performance Optimized** - High-performance caching and data processing
4. **Security by Design** - Multi-layer security with encryption and monitoring
5. **Modular Architecture** - Clean separation of concerns for maintainability
6. **Real-time Collaboration** - Live updates and communication across all components

## System Architecture

The TripSage platform follows a layered architecture with clear separation between presentation, application, business logic, and infrastructure layers.

```plaintext
┌─────────────────────────────────────────────────────────────────────────────┐
│                           TripSage AI Platform                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                          Presentation Layer                                │
│  ┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────┐  │
│  │     Frontend        │    │    AI Agents        │    │  External APIs  │  │
│  │   (Next.js 15)      │    │   (LangGraph)       │    │  (Travel Svcs)  │  │
│  │                     │    │                     │    │                 │  │
│  │ • React Components  │    │ • Planning Agent    │    │ • Flight APIs   │  │
│  │ • Real-time UI      │    │ • Flight Agent      │    │ • Hotel APIs    │  │
│  │ • Chat Interface    │    │ • Hotel Agent       │    │ • Maps APIs     │  │
│  │ • Trip Planning     │    │ • Budget Agent      │    │ • Weather APIs  │  │
│  │ • User Management   │    │ • Memory Agent      │    │ • Calendar APIs │  │
│  └─────────────────────┘    └─────────────────────┘    └─────────────────┘  │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Application Layer                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                      Unified API (FastAPI)                         │    │
│  │                                                                     │    │
│  │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐    │    │
│  │ │ Consumer    │ │ Auth &      │ │ Rate        │ │ Response    │    │    │
│  │ │ Detection   │ │ Security    │ │ Limiting    │ │ Formatting  │    │    │
│  │ └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘    │    │
│  │                                                                     │    │
│  │ ┌─────────────────────────────────────────────────────────────┐    │    │
│  │ │                    API Routers                              │    │    │
│  │ │ Auth│Trips│Chat│Flights│Hotels│Destinations│Memory│WebSocket│    │    │
│  │ └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                           Business Logic Layer                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        TripSage Core                               │    │
│  │                                                                     │    │
│  │ ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────┐    │    │
│  │ │ Business        │ │ External API    │ │ Infrastructure      │    │    │
│  │ │ Services        │ │ Services        │ │ Services            │    │    │
│  │ │                 │ │                 │ │                     │    │    │
│  │ │ • Auth Service  │ │ • Google Maps   │ │ • Database Service  │    │    │
│  │ │ • Memory Svc    │ │ • Weather API   │ │ • Cache Service     │    │    │
│  │ │ • Chat Service  │ │ • Calendar API  │ │ • WebSocket Mgr     │    │    │
│  │ │ • Flight Svc    │ │ • Document AI   │ │ • Key Monitoring    │    │    │
│  │ │ • Hotel Service │ │ • WebCrawl Svc  │ │ • Security Service  │    │    │
│  │ └─────────────────┘ └─────────────────┘ └─────────────────────┘    │    │
│  │                                                                     │    │
│  │ ┌─────────────────────────────────────────────────────────────┐    │    │
│  │ │              Shared Models & Schemas                       │    │    │
│  │ │ Database Models │ Domain Models │ API Schemas │ Validators │    │    │
│  │ └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────────────────────────────┤
│                         Infrastructure Layer                               │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐    │
│  │   Database      │ │      Cache      │ │       External Services     │    │
│  │   (Supabase)    │ │  (DragonflyDB)  │ │                             │    │
│  │                 │ │                 │ │ ┌─────────┐ ┌─────────────┐ │    │
│  │ • PostgreSQL    │ │ • Redis-compat  │ │ │ Duffel  │ │ Google      │ │    │
│  │ • pgvector      │ │ • 25x faster    │ │ │ Flights │ │ Maps/Cal    │ │    │
│  │ • Row Level     │ │ • Multi-tier    │ │ └─────────┘ └─────────────┘ │    │
│  │   Security      │ │   TTL strategy  │ │                             │    │
│  │ • Migrations    │ │ • Intelligent   │ │ ┌─────────┐ ┌─────────────┐ │    │
│  │ • Backups       │ │   invalidation  │ │ │ Weather │ │ Airbnb MCP  │ │    │
│  └─────────────────┘ └─────────────────┘ │ │   API   │ │ Integration │ │    │
│                                          │ └─────────┘ └─────────────┘ │    │
│                                          └─────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Component Overview

### Frontend Layer (Next.js 15) - Grade A Implementation

**Modern React-based web application with exceptional quality:**

- **App Router** - Modern routing with server-side rendering and streaming SSR ready
- **Component Architecture** - Professional-grade modular components with shadcn-ui
- **Real-time Features** - Comprehensive WebSocket client (804 lines) ready for backend connection
- **State Management** - Zustand v5 stores with React Query v5 integration
- **Error Boundaries** - Production-ready error handling and recovery
- **Performance Optimization** - React 19 Compiler ready, code splitting implemented
- **Authentication System** - Complete JWT-based authentication UI with route protection
- **Testing Excellence** - 85-90% coverage with Vitest, Playwright E2E tests

**Implemented Features (60-70% Complete):**

- ✅ Travel planning interface with advanced itinerary building
- ✅ Real-time agent monitoring dashboard with predictive analytics
- ✅ Chat interface with typing indicators and attachment support
- ✅ Trip collaboration and sharing interfaces
- ✅ Budget tracking and expense management UI
- ✅ Interactive maps and destination exploration
- ✅ Mobile-responsive design with PWA capabilities
- 🔄 Backend API integration (requires authentication connection)
- 🔄 WebSocket real-time features (infrastructure ready, needs backend)

### Unified API Layer (FastAPI) - 92% Complete

**Consumer-aware API serving both frontend and agents:**

- **Dual Consumer Support** - Automatic adaptation for frontend vs. agent consumers
- **Authentication Systems** - JWT for users, API keys for agents, BYOK for external services
- **Rate Limiting** - Consumer-aware limits with enhanced principal tracking  
- **WebSocket Support** - Real-time communication infrastructure ready
- **Performance Optimization** - Multi-tier caching and query optimization
- **Security** - Multi-layer security with encryption and monitoring

**Consumer Adaptations:**

- **Frontend**: User-friendly errors, UI metadata, sanitized responses
- **Agents**: Technical context, tool suggestions, raw data access

**Integration Gaps Requiring Immediate Attention:**

- 🔄 **Authentication Integration**: Frontend JWT system needs backend FastAPI service connection
- 🔄 **Missing Backend Routers**: activities.py and search.py endpoints required  
- 🔄 **WebSocket Connection**: Infrastructure ready on both ends, needs activation
- ✅ **Security**: JWT security hardening completed - production security implemented

### AI Agent Layer (LangGraph)

**Intelligent travel planning agents with specialized capabilities:**

#### Core Agents

- **Planning Agent** - Master coordinator for complex trip planning
- **Flight Agent** - Flight search, booking, and price tracking
- **Accommodation Agent** - Hotel and lodging search with MCP integration
- **Budget Agent** - Cost optimization and expense tracking
- **Destination Agent** - Research and recommendations
- **Memory Agent** - Context management and user learning

#### Agent Capabilities

- **Multi-step Planning** - Complex workflows with checkpoints
- **Tool Integration** - Rich tool calling with external services
- **Memory Integration** - Persistent context across conversations
- **Error Recovery** - Intelligent error handling and retry logic
- **Handoff Coordination** - Seamless agent collaboration

### TripSage Core Layer

**Shared foundation providing:**

#### Business Services

- **AuthService** - Authentication and authorization
- **MemoryService** - Conversation memory and context (91% faster with Mem0)
- **ChatService** - Chat orchestration and processing
- **FlightService** - Flight operations and booking
- **AccommodationService** - Hotel and lodging services
- **DestinationService** - Research and recommendations
- **TripService** - Trip planning and coordination

#### Infrastructure Services

- **DatabaseService** - Supabase integration with transactions
- **CacheService** - DragonflyDB with intelligent TTL (25x improvement)
- **WebSocketManager** - Real-time communication
- **KeyMonitoringService** - API key security and usage tracking

### Infrastructure Layer

#### Database (Supabase PostgreSQL)

- **Primary Storage** - User data, trips, bookings, preferences
- **pgvector Extension** - AI embeddings for similarity search
- **Row Level Security** - Fine-grained access control
- **Real-time Subscriptions** - Live data updates
- **Migration System** - Version-controlled schema changes

#### Cache (DragonflyDB)

- **High Performance** - 25x faster than Redis
- **Multi-tier Strategy** - Hot/warm/cold data with intelligent TTL
- **Redis Compatibility** - Drop-in Redis replacement
- **Memory Efficiency** - Optimized for large datasets

#### External Integrations

- **Flight APIs** - Duffel for comprehensive flight data
- **Accommodation** - Airbnb MCP integration for alternative lodging
- **Maps & Location** - Google Maps for geographic services
- **Weather** - OpenWeatherMap for travel conditions
- **Calendar** - Google Calendar for trip scheduling

## Data Flow Architecture

### User Request Flow

```mermaid
sequenceDiagram
    participant U as User (Frontend)
    participant A as API Gateway
    participant B as Business Service
    participant C as Cache
    participant D as Database
    participant E as External API

    U->>A: Request (JWT/API Key)
    A->>A: Authenticate & Detect Consumer
    A->>A: Rate Limiting Check
    A->>B: Route to Business Service
    B->>C: Check Cache
    
    alt Cache Hit
        C->>B: Return Cached Data
    else Cache Miss
        B->>E: Call External API
        E->>B: Return Data
        B->>C: Store in Cache
        B->>D: Store in Database
    end
    
    B->>A: Return Response
    A->>A: Format for Consumer Type
    A->>U: Response (Formatted)
```

### Agent Interaction Flow

```mermaid
sequenceDiagram
    participant AG as AI Agent
    participant API as Unified API
    participant ORG as Agent Orchestrator
    participant MEM as Memory Service
    participant EXT as External Services

    AG->>API: Tool Call Request
    API->>API: Detect Agent Consumer
    API->>ORG: Route to Orchestrator
    ORG->>MEM: Get Context
    MEM->>ORG: Return Context
    ORG->>EXT: Execute Tool
    EXT->>ORG: Return Results
    ORG->>MEM: Store Results
    ORG->>API: Return Rich Response
    API->>AG: Agent-Optimized Response
```

### Real-time Communication Flow

```mermaid
graph TD
    A[User Action] --> B[WebSocket Manager]
    B --> C[Event Router]
    C --> D[Agent Orchestrator]
    D --> E[Business Services]
    E --> F[External APIs]
    F --> G[Response Processing]
    G --> H[Event Broadcasting]
    H --> I[Connected Clients]
    
    J[Agent Processing] --> K[Status Updates]
    K --> L[WebSocket Broadcast]
    L --> M[Frontend Updates]
```

## Integration Architecture

### External Service Integration Pattern

The platform uses a standardized pattern for integrating with external services:

```python
# Unified external service integration
class ExternalServiceIntegration:
    """Standardized pattern for external API integration"""
    
    async def call_service(self, user_id: str, service: str, operation: str):
        # 1. Try user's BYOK key first
        user_key = await self.get_user_key(user_id, service)
        if user_key:
            try:
                return await self.make_api_call(service, operation, user_key)
            except Exception:
                logger.warning(f"User key failed for {service}, falling back")
        
        # 2. Fallback to system key
        system_key = self.get_system_key(service)
        return await self.make_api_call(service, operation, system_key)
```

### Memory Integration Pattern

Persistent memory across all components:

```python
# Memory integration across the platform
class MemoryIntegration:
    """Unified memory system for context persistence"""
    
    async def store_interaction(self, user_id: str, interaction: dict):
        # Store in vector database for similarity search
        await self.vector_store.store(
            user_id=user_id,
            content=interaction,
            embedding=await self.generate_embedding(interaction)
        )
        
        # Store structured data in relational database
        await self.db.store_interaction(user_id, interaction)
        
        # Update real-time context cache
        await self.cache.update_user_context(user_id, interaction)
```

### BYOK (Bring Your Own Key) Integration

Secure user-provided API key management:

```python
# BYOK system integration
class BYOKIntegration:
    """Secure user API key management"""
    
    async def store_user_key(self, user_id: str, service: str, api_key: str):
        # 1. Validate key with service
        is_valid = await self.validate_key(service, api_key)
        if not is_valid:
            raise ValidationError("Invalid API key")
        
        # 2. Encrypt with user-specific salt
        user_salt = self.generate_user_salt(user_id)
        encrypted_key = self.encrypt(api_key, user_salt)
        
        # 3. Store securely
        await self.db.store_encrypted_key(user_id, service, encrypted_key)
        
        # 4. Monitor usage
        await self.monitoring.setup_key_monitoring(user_id, service)
```

## Deployment Architecture

### Container Orchestration

The platform is designed for containerized deployment with Kubernetes:

```yaml
# Example deployment configuration
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tripsage-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: tripsage-api
  template:
    metadata:
      labels:
        app: tripsage-api
    spec:
      containers:
      - name: api
        image: tripsage/api:latest
        resources:
          requests:
            cpu: "1"
            memory: "2Gi"
          limits:
            cpu: "2"
            memory: "4Gi"
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-secret
              key: url
        ports:
        - containerPort: 8000
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
```

### Microservice Deployment

Each major component can be deployed independently:

- **Frontend Service** - Next.js application with CDN distribution
- **API Service** - FastAPI with auto-scaling based on load
- **Agent Service** - LangGraph agents with dedicated compute resources
- **Memory Service** - Dedicated Mem0 service with vector database
- **Cache Service** - DragonflyDB cluster with high availability

### Environment Management

Multi-environment deployment strategy:

- **Development** - Local development with docker-compose
- **Staging** - Pre-production testing with reduced resources
- **Production** - Full-scale deployment with monitoring and alerts

## Performance Architecture

### Caching Strategy

Multi-tier caching for optimal performance:

```python
# Intelligent caching strategy
class CachingStrategy:
    TIERS = {
        "hot": {
            "ttl": 300,  # 5 minutes
            "data_types": ["flight_prices", "availability", "user_sessions"]
        },
        "warm": {
            "ttl": 3600,  # 1 hour  
            "data_types": ["search_results", "destination_info", "weather"]
        },
        "cold": {
            "ttl": 86400,  # 24 hours
            "data_types": ["user_preferences", "historical_data", "static_content"]
        }
    }
```

### Database Optimization

- **Connection Pooling** - Efficient database connection management
- **Query Optimization** - Indexed searches and prepared statements
- **Read Replicas** - Distributed read operations for scalability
- **Partitioning** - Time-based partitioning for large datasets

### Memory Optimization

- **Vector Search** - pgvector for efficient similarity search
- **Context Compression** - Intelligent context summarization
- **Memory Tiering** - Hot/warm/cold memory management
- **Garbage Collection** - Automatic cleanup of old memories

## Security Architecture

### Multi-Layer Security

```python
# Comprehensive security implementation
class SecurityArchitecture:
    LAYERS = [
        "network_security",    # HTTPS, firewall, VPN
        "authentication",      # JWT, API keys, BYOK
        "authorization",       # RBAC, resource-level permissions
        "input_validation",    # Request sanitization, SQL injection prevention
        "rate_limiting",       # DDoS protection, abuse prevention
        "encryption",         # AES-256 for sensitive data
        "monitoring",         # Security event tracking
        "audit_logging"       # Compliance and forensics
    ]
```

### Data Protection

- **Encryption at Rest** - All sensitive data encrypted in database
- **Encryption in Transit** - TLS 1.3 for all communications
- **Key Rotation** - Automatic encryption key rotation
- **Data Minimization** - Only collect and store necessary data
- **Right to Deletion** - GDPR-compliant data deletion

### Compliance

- **GDPR Compliance** - European data protection regulations
- **CCPA Compliance** - California consumer privacy protection
- **SOC 2 Type II** - Security and availability controls
- **Data Residency** - Geographic data storage controls

## Integration Benefits

The unified architecture provides several key benefits:

### For Developers

- **Consistent APIs** - Single interface for all functionality
- **Shared Components** - Reusable services and models
- **Type Safety** - End-to-end type checking with Pydantic and Zod
- **Comprehensive Testing** - Integrated testing framework

### For Users

- **Seamless Experience** - Consistent interface across web and mobile
- **Real-time Collaboration** - Live updates and shared planning
- **Intelligent Assistance** - AI agents that learn and adapt
- **Privacy Protection** - Secure data handling and user control

### For Operations

- **Scalable Architecture** - Independent scaling of components
- **Monitoring & Observability** - Comprehensive metrics and logging
- **High Availability** - Redundant systems and automatic failover
- **Performance Optimization** - Intelligent caching and query optimization

## Implementation Roadmap (Based on June 2025 Review)

### Critical Path to Production (5-6 Weeks)

**Phase 1: Security & Authentication (Week 1)**
- ✅ Remove hardcoded JWT fallback secret (security vulnerability) - **Completed June 6, 2025**
- ✅ Implement production JWT security patterns - **Completed June 6, 2025**
- 🔄 Connect frontend authentication to backend JWT service
- 🔄 Implement secure token refresh mechanism

**Phase 2: Backend API Completion (Week 2-3)**
- Add missing activities.py router (search, booking, availability)
- Add missing search.py router (unified search, suggestions)
- Integrate service layer with existing patterns

**Phase 3: Real-time Feature Connection (Week 3-4)**
- Connect WebSocket infrastructure (ready on both ends)
- Replace mock agent data with real-time status updates
- Implement chat functionality with backend message routing

**Phase 4: Test Infrastructure Modernization (Week 4-5)**
- Fix 527 failing tests with Pydantic v1→v2 migration
- Achieve ≥90% test coverage across frontend and backend

**Phase 5: Performance & Production (Week 5-6)**
- Enable React 19 Compiler for automatic optimizations
- Move rate limiting to DragonflyDB
- Production deployment with comprehensive monitoring

### Future Enhancements

1. **Mobile Applications** - Native iOS and Android apps
2. **Advanced AI Features** - Enhanced agent collaboration
3. **Global Expansion** - Multi-region deployment
4. **Enterprise Features** - Advanced security and compliance

### Success Metrics

- **Frontend Quality**: Grade A maintained with 85-90% test coverage (on track for A+)
- **Security**: JWT hardening completed, zero critical vulnerabilities remaining
- **Performance**: Core Web Vitals in green zone, <100ms WebSocket latency (infrastructure ready)
- **User Experience**: <2s authentication (foundation complete), real-time collaboration features ready

The TripSage architecture successfully balances cutting-edge technology with production reliability, demonstrating exceptional frontend implementation quality while addressing critical integration gaps for production readiness.
