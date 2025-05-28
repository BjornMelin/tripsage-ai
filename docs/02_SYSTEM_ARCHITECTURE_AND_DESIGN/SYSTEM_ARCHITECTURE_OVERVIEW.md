# TripSage System Architecture Overview

This document outlines the high-level architecture of the TripSage AI Travel Planning System. It describes the main components, their interactions, and the overall design philosophy that guides the system's development.

## 1. High-Level Architecture Diagram

The TripSage system is designed as a modular, service-oriented architecture, enabling flexibility and scalability. The core components interact as follows:

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│                     TripSage Orchestration Layer                     │
│                (Handles core logic, agent coordination)             │
├─────────────────────────────────────────────────────────────────────┤
│                    🚀 UNIFIED SERVICE INTEGRATION                    │
│     Direct SDK Integration (7 Services) + Airbnb MCP (1 Service)    │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Duffel SDK  │  │Weather APIs │  │ Python      │  │ Crawl4AI    │ │
│  │ (Flights)   │  │ (Direct)    │  │ datetime    │  │ SDK         │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Supabase    │  │ Mem0 +      │  │ Playwright  │  │ Airbnb MCP  │ │
│  │ SDK         │  │ pgvector    │  │ SDK         │  │ (Only MCP)  │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘ │
├─────────────────────────────────────────────────────────────────────┤
│                       OpenAI Agents SDK Adapters                     │
│                  (Function tools, agent definitions)                │
├─────────────────────────────────────────────────────────────────────┤
│                       Agent Implementation                           │
│                  (Travel, Budget, Itinerary Agents)                 │
├───────────────────┬───────────────────────┬─────────────────────────┤
│  Travel Planning  │   Budget Planning     │  Itinerary Planning     │
│       Agent       │       Agent           │        Agent            │
├───────────────────┴───────────────────────┴─────────────────────────┤
│                        FastAPI Backend                               │
│              (User Auth, API Endpoints, Business Logic)             │
├─────────────────────────────────────────────────────────────────────┤
│                      UNIFIED STORAGE ARCHITECTURE                    │
│    Supabase PostgreSQL + pgvector + DragonflyDB Cache               │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. Component Overview

TripSage's architecture consists of several key layers:

1. **Frontend Layer (Not detailed in this document)**:

    - Next.js application serving the user interface.
    - Interacts with the FastAPI Backend.

2. **FastAPI Backend**:

    - Python-based API server handling core business logic, user authentication, and client communication.
    - Serves as the main entry point for frontend requests.

3. **Agent Implementation Layer**:

    - Contains the AI agents (e.g., Travel Planning Agent, Budget Agent, Itinerary Agent) built using the OpenAI Agents SDK.
    - These agents orchestrate tasks and interact with various tools and services.

4. **OpenAI Agents SDK Adapters**:

    - Provides the function tools and definitions that bridge the agents' capabilities with the underlying MCP services and other utilities.

5. **Integration & Abstraction Layer (MCP Abstraction Layer)**:

    - A crucial layer that standardizes how agents and the backend interact with various Model Context Protocol (MCP) servers.
    - It ensures consistent interfaces, error handling, and configuration management for all MCP communications.
    - Includes the MCP Manager, MCP Client Registry, and specific MCP Wrappers.

6. **Service Integration Layer**:

    - **Direct SDK Integration**: 7 services now use direct SDK/API integration (Flights via Duffel SDK, Weather via direct APIs, Time via Python datetime, Web Crawling via Crawl4AI SDK, Browser Automation via Playwright SDK, Database via Supabase SDK, Memory via Mem0 + pgvector).
    - **Single MCP Server**: Only Airbnb accommodation functionality remains as an MCP server integration.
    - **Performance Benefit**: 50-70% latency reduction and 6-10x crawling improvement compared to MCP abstraction.

7. **Storage Layer (Unified Storage Architecture)**:
    - **Primary Database (Supabase PostgreSQL)**: Unified storage for all structured data including user profiles, trip details, bookings, cached API responses, and vector embeddings via pgvector extension.
    - **Vector Search (pgvector)**: Integrated directly into Supabase PostgreSQL for semantic search capabilities, replacing separate vector database needs.
    - **Memory System (Mem0 + pgvector)**: Handles travel entity relationships, user preferences, and contextual information using Mem0 with Supabase as the backend.
    - **High-Performance Cache (DragonflyDB)**: Replaces Redis with 25x performance improvement for caching API responses, search results, and frequently accessed data.

## 3. Service Integration Architecture

> **📢 ARCHITECTURE UPDATE**: TripSage has migrated from a complex MCP-centric architecture to a simplified direct SDK integration approach for maximum performance.

The Service Integration Architecture provides a unified way for TripSage agents and backend services to interact with external services through direct SDK integration, with minimal MCP server usage.

### 3.1. Current Service Integration Pattern

The simplified architecture uses direct SDK integration with service abstraction for consistency:

```plaintext
┌─────────────────────────────────────────┐
│           Agent/Tool/Service            │
│ (e.g., Travel Agent, FastAPI endpoint)  │
└─────────────────┬───────────────────────┘
                  │ Direct method calls
                  ▼
┌─────────────────────────────────────────┐
│        Service Manager (Simplified)     │
│  - Direct SDK client initialization     │
│  - Standardized error handling & logging│
│  - Unified configuration management     │
└─────────────────┬───────────────────────┘
                  │ Direct SDK access
                  ▼
┌─────────────────────────────────────────┐
│           DIRECT SDK INTEGRATIONS       │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ Duffel SDK   │  │ Weather APIs  │   │
│  │ (Flights)    │  │ (Direct HTTP) │   │
│  └──────────────┘  └───────────────┘   │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ Supabase SDK │  │ Crawl4AI SDK  │   │
│  │ + Mem0       │  │ + Playwright  │   │
│  └──────────────┘  └───────────────┘   │
│                                         │
│  ┌───────────────────────────────────┐ │
│  │        Only Remaining MCP:        │ │
│  │       Airbnb MCP Server           │ │
│  └───────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

### 3.2. Key Components of the Service Integration Layer

- **Service Manager (Simplified)**:

  - Central orchestrator for service operations with reduced complexity
  - Loads configurations for all services from the centralized settings system
  - Initializes direct SDK clients as needed
  - Implements standardized error handling and logging for all service interactions

- **Direct SDK Clients**:

  - **Duffel SDK Client**: Direct integration with Duffel API for flight services
  - **Weather API Clients**: Direct HTTP clients for weather data providers
  - **Supabase SDK Client**: Direct integration with Supabase for database operations
  - **Mem0 Client**: Direct integration for memory system operations
  - **Crawl4AI Client**: Direct SDK integration for web crawling
  - **Playwright Client**: Direct SDK integration for browser automation

- **Single MCP Integration (`AirbnbMCPWrapper`)**:
  - Only remaining MCP server integration for accommodation services
  - Maintains compatibility with existing MCP patterns for this specific service
  - Will be evaluated for future SDK migration

- **Service Abstraction Interfaces**:
  - Standardized Python interfaces for each service type
  - Consistent error handling and response formatting
  - Type-safe method signatures using Pydantic models

### 3.3. Design Patterns Used

- **Service Manager Pattern**: The simplified `ServiceManager` coordinates service operations with reduced complexity
- **Direct Integration Pattern**: Services use their native SDKs directly without abstraction overhead
- **Factory Pattern**: Service clients are instantiated through factory methods for consistency
- **Singleton Pattern**: Service managers maintain singleton instances for efficiency and consistency

### 3.4. Key Features and Benefits

- **Performance Optimized**: Direct SDK integration provides 50-70% latency reduction compared to MCP abstraction layers.

  ```python
  # Direct SDK usage example
  from duffel_api import Duffel
  from supabase import create_client
  
  # Direct flight search
  duffel = Duffel(api_key=settings.duffel_api_key)
  offers = await duffel.offer_requests.create(search_params)
  
  # Direct database operation
  supabase = create_client(settings.supabase_url, settings.supabase_key)
  result = await supabase.table('trips').insert(trip_data).execute()
  ```

- **Simplified Architecture**:
  - Reduced complexity from 12 MCP servers to 7 direct SDK integrations + 1 MCP
  - Eliminates unnecessary abstraction layers and serialization overhead
  - Direct access to full SDK feature sets and advanced configurations

- **Enhanced Type Safety**:
  - Native SDK type hints and Pydantic models for data validation
  - Direct access to provider-specific type definitions
  - Reduced type conversion and mapping complexity

- **Unified Configuration**:
  - All service configurations managed through centralized `AppSettings`
  - Environment variable based configuration for all services
  - Consistent credential and endpoint management

- **Improved Error Handling**:
  - Direct access to provider-specific error details
  - Reduced error wrapping and abstraction layers
  - Native retry and circuit breaker patterns where supported

- **Developer Experience**:
  - Familiar SDK patterns for Python developers
  - Full access to documentation and community resources for each service
  - Reduced learning curve for new team members

- **Maintenance Benefits**:
  - Fewer custom abstractions to maintain
  - Direct dependency on well-maintained SDKs
  - Reduced internal code surface area (~3000 lines eliminated)

## 4. Data Flow

A typical data flow for a user request in the simplified architecture:

1. **User Interaction**: User makes a request through the Frontend (e.g., search for flights).
2. **API Request**: Frontend sends a request to the FastAPI Backend.
3. **Agent Invocation**: Backend invokes the appropriate AI Agent (e.g., Travel Planning Agent).
4. **Tool Selection**: The Agent determines the need to use one or more tools, which directly call service SDKs.
5. **Direct Service Interaction**:
    - The Agent's tool directly calls the relevant SDK (e.g., Duffel SDK for flights)
    - No abstraction layers or MCP overhead
    - Direct access to provider APIs and features
6. **Data Retrieval/Processing**: The SDK performs its task (e.g., calls Duffel API, queries Supabase).
7. **Response Processing**: The response flows directly back to the Agent tool and Agent.
8. **Data Storage**: Relevant information is stored directly in Supabase PostgreSQL using the Supabase SDK, with vector embeddings handled via pgvector.
9. **Memory Updates**: Contextual information is stored using Mem0 with Supabase backend for enhanced agent reasoning.
10. **Backend Response**: The FastAPI Backend formats the final response.
11. **UI Update**: The Frontend receives the response and updates the user interface.

This simplified architecture eliminates abstraction overhead while maintaining separation of concerns, resulting in significantly improved performance and reduced complexity. The direct SDK integration approach provides better error handling, type safety, and developer experience.
