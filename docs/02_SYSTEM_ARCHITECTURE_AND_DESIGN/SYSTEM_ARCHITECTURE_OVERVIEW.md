# TripSage System Architecture Overview

This document outlines the high-level architecture of the TripSage AI Travel Planning System. It describes the main components, their interactions, and the overall design philosophy that guides the system's development.

## 1. High-Level Architecture Diagram

The TripSage system is designed as a modular, service-oriented architecture, enabling flexibility and scalability. The core components interact as follows:

```plaintext
┌─────────────────────────────────────────────────────────────────────┐
│                     TripSage Orchestration Layer                     │
│                (Handles core logic, agent coordination)             │
├─────────┬─────────┬─────────┬──────────┬──────────┬─────────────────┤
│ Weather │  Web    │ Flights │Accommoda-│ Calendar │    Memory       │
│   MCP   │ Crawl   │   MCP   │tion MCP  │   MCP    │     MCP         │
│ Server  │ MCP     │ Server  │ Server   │  Server  │    Server       │
│         │ Server  │         │          │          │ (Neo4j)         │
├─────────┴─────────┴─────────┴──────────┴──────────┼─────────────────┤
│                    Integration & Abstraction Layer │  Vector Search  │
│                 (MCP Manager, Wrappers, Registry)  │  (Qdrant -     │
│                                                    │   Post-MVP)     │
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
│                      Primary Database (Relational)                   │
│              (Supabase - Prod / Neon - Dev)                        │
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

6. **MCP Server Layer**:

   - A suite of specialized microservices, each providing domain-specific functionality (e.g., weather, flights, accommodations, knowledge graph memory).
   - Most are built using Python FastMCP 2.0 for custom logic or integrate official/external MCP implementations.

7. **Storage Layer (Dual Storage Architecture)**:
   - **Relational Database (Supabase/Neon)**: Primary storage for structured data like user profiles, trip details, bookings, and cached API responses. Supabase is used for production, while Neon is used for development due to its branching capabilities.
   - **Knowledge Graph (Neo4j via Memory MCP)**: Stores travel entity relationships, user preferences, historical travel patterns, and contextual information to enhance AI agent reasoning and recommendations.
   - **Vector Search (Qdrant - Post-MVP)**: Planned for future integration to enable advanced semantic search capabilities.
   - **Redis Cache**: Used for caching API responses, search results, and other frequently accessed data to improve performance and reduce external API calls.

## 3. MCP Abstraction Layer

The MCP Abstraction Layer is designed to provide a unified and consistent way for the TripSage system (primarily AI agents and backend services) to interact with a diverse set of external and internal MCP servers.

### 3.1. Architecture of the Abstraction Layer

The layer employs a Manager/Registry pattern with type-safe wrapper interfaces:

```plaintext
┌─────────────────────────────────────────┐
│           Agent/Tool/Service            │
│ (e.g., Travel Agent, FastAPI endpoint)  │
└─────────────────┬───────────────────────┘
                  │ .invoke(mcp_name, method, params)
                  ▼
┌─────────────────────────────────────────┐
│            MCP Manager                  │
│  - Configuration loading (from settings)│
│  - Client initialization & pooling      │
│  - Method invocation routing            │
│  - Standardized error handling & logging│
└─────────────────┬───────────────────────┘
                  │ .get_wrapper(mcp_name)
                  ▼
┌─────────────────────────────────────────┐
│          MCP Client Registry            │
│  - Wrapper class registration           │
│  - Singleton instance management        │
└─────────────────┬───────────────────────┘
                  │ .create_instance()
                  ▼
┌─────────────────────────────────────────┐
│         MCP Wrappers (BaseMCPWrapper)   │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ Playwright   │  │ Google Maps   │   │
│  │ Wrapper      │  │ Wrapper       │   │
│  │ (Connects to │  │ (Connects to  │   │
│  │ PlaywrightMCP)│  │ GoogleMapsMCP)│   │
│  └──────────────┘  └───────────────┘   │
│  ┌──────────────┐  ┌───────────────┐   │
│  │ Weather      │  │ ... Other     │   │
│  │ Wrapper      │  │ Wrappers ...  │   │
│  └──────────────┘  └───────────────┘   │
└─────────────────────────────────────────┘
```

### 3.2. Key Components of the Abstraction Layer

- **MCP Manager (`MCPManager`)**:

  - The central orchestrator for all MCP operations.
  - Loads configurations for all registered MCPs from the centralized settings system.
  - Initializes MCP client wrappers as needed.
  - Provides a unified `invoke` method to call any tool on any registered MCP server.
  - Implements standardized error handling, logging, and potentially metrics for MCP interactions.

- **MCP Client Registry (`MCPClientRegistry`)**:

  - Maintains a mapping of MCP names (e.g., "weather", "flights") to their respective wrapper classes.
  - Ensures that MCP wrapper classes are registered during application startup.
  - Manages the instantiation of wrapper objects (often as singletons).

- **Base MCP Wrapper (`BaseMCPWrapper`)**:

  - An abstract base class or protocol that defines the standard interface all specific MCP wrappers must implement.
  - This includes methods like `invoke_method`, `get_available_methods`, and `get_client`.
  - Handles common functionalities like client instantiation based on configuration and basic error wrapping.

- **Specific MCP Wrappers** (e.g., `WeatherMCPWrapper`, `FlightsMCPWrapper`):
  - Concrete implementations of `BaseMCPWrapper` for each specific MCP server type.
  - Encapsulate the logic for interacting with a particular MCP client library (e.g., the Python client for the Duffel Flights MCP).
  - Map standardized method names (used by the `MCPManager.invoke` call) to the actual method names of the underlying MCP client.
  - May include specific data transformation logic if the raw MCP response needs adaptation for TripSage's internal models.

### 3.3. Design Patterns Used

- **Manager Pattern**: The `MCPManager` centralizes the control and coordination of MCP interactions.
- **Registry Pattern**: The `MCPClientRegistry` allows for dynamic discovery and registration of MCP wrapper implementations.
- **Wrapper/Adapter Pattern**: Each specific MCP wrapper adapts the interface of an external MCP client to a common internal interface defined by `BaseMCPWrapper`.
- **Singleton Pattern**: The `MCPManager` and `MCPClientRegistry` are typically implemented as singletons to ensure a single point of control and configuration.

### 3.4. Key Features and Benefits

- **Consistent Interface**: All MCP interactions, regardless of the specific server, are performed through the `MCPManager.invoke` method or by obtaining a wrapper with a standard interface.

  ```python
  # Using the manager
  result = await mcp_manager.invoke(
      mcp_name="weather",
      method_name="get_current_weather",
      params={"city": "New York"}
  )

  # Direct wrapper access for more specific control if needed
  weather_wrapper = await mcp_manager.get_wrapper("weather")
  if weather_wrapper:
      result = await weather_wrapper.invoke_method("get_current_weather", params={"city": "New York"})
  ```

- **Type Safety**:
  - Pydantic models are used for MCP configurations within the centralized settings.
  - Generic type parameters in base classes (e.g., `BaseMCPWrapper[SpecificMCPClientType]`) help maintain type hints.
  - Method signatures in wrappers and the manager use strong typing.
- **Centralized Configuration Management**:
  - MCP server endpoints, API keys, and other parameters are loaded from the `AppSettings` (via `mcp_settings.py` or equivalent).
  - This allows for easy configuration changes through environment variables or `.env` files without code modification.
- **Standardized Error Handling**:
  - The `MCPManager` and `BaseMCPWrapper` implement a common error handling strategy.
  - External MCP errors are caught and wrapped into a standardized TripSage MCPError hierarchy (e.g., `MCPConnectionError`, `MCPToolExecutionError`).
  - This provides consistent error messages and categorization to the calling code.
- **Simplified Agent/Tool Development**:
  - Developers creating agent tools or backend services that need to call MCPs don't need to know the specifics of each individual MCP client library. They interact with the consistent `MCPManager` interface.
  - Reduces boilerplate code for client instantiation, configuration loading, and error handling in each tool.
- **Extensibility**:
  - Adding a new MCP integration involves:
    1. Creating a new specific wrapper class inheriting from `BaseMCPWrapper`.
    2. Implementing the method mapping and any specific logic for that MCP.
    3. Registering the new wrapper with the `MCPClientRegistry`.
    4. Adding its configuration to the centralized settings.
- **Testability**:
  - The `MCPManager` or individual wrappers can be easily mocked during testing, allowing for isolated unit tests of components that depend on MCP interactions.

## 4. Data Flow

A typical data flow for a user request might be:

1. **User Interaction**: User makes a request through the Frontend (e.g., search for flights).
2. **API Request**: Frontend sends a request to the FastAPI Backend.
3. **Agent Invocation**: Backend invokes the appropriate AI Agent (e.g., Travel Planning Agent).
4. **Tool Selection**: The Agent determines the need to use one or more tools, which are often interfaces to MCP servers.
5. **MCP Interaction**:
   - The Agent's tool calls the `MCPManager`.
   - The `MCPManager` uses the `MCPClientRegistry` to get the appropriate MCP Wrapper.
   - The Wrapper interacts with the target MCP Server (e.g., Flights MCP).
6. **Data Retrieval/Processing**: The MCP Server performs its task (e.g., calls Duffel API, queries Neo4j).
7. **Response Propagation**: The response flows back through the Wrapper, Manager, Agent tool, and Agent.
8. **Data Storage**: Relevant information from the interaction may be stored in the Relational Database (Supabase/Neon) and/or the Knowledge Graph (Neo4j via Memory MCP).
9. **Backend Response**: The FastAPI Backend formats the final response.
10. **UI Update**: The Frontend receives the response and updates the user interface.

This layered architecture promotes separation of concerns, making the system easier to develop, test, and maintain. The MCP Abstraction Layer is key to managing the complexity of integrating multiple specialized services.
