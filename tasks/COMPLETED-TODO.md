# Completed Tasks from TODO.md

This file contains all the tasks that were marked as completed in the main TODO.md file.

- [x] **Redis MCP Integration (PR #97):**
  - ✓ Implemented RedisMCPWrapper with comprehensive Redis operations support
  - ✓ Created RedisMCPClient with connection management and Redis interface
  - ✓ Developed distributed locking capabilities (acquire_lock, release_lock, extend_lock)
  - ✓ Implemented pipeline execution for improved performance
  - ✓ Added content-aware TTL management based on data volatility
  - ✓ Created comprehensive cache tools with decorators for different content types
  - ✓ Implemented batch operations (batch_cache_set, batch_cache_get, batch_cache_delete)
  - ✓ Added cache prefetching and warming capabilities
  - ✓ Enhanced CachedWebSearchTool with distributed locking
  - ✓ Improved WebSearchTool with batch operations and performance monitoring
  - ✓ Added comprehensive test suite for cache tools and Redis MCP integration
  - ✓ Created detailed documentation in docs/05_SEARCH_AND_CACHING/REDIS_MCP_INTEGRATION.md
  - ✓ Developed metrics collection framework for cache operations
  - ✓ Implemented distributed coordination for cache invalidation
  - ✓ Added cache key management and namespacing system
  - ✓ Created cache_context manager for resource management
  - ✓ Integrated with existing WebOperationsCache architecture

- [x] **Agent Handoffs Optimization:**
  - ✓ Conducted comprehensive research on latest OpenAI Agents SDK handoff best practices
  - ✓ Updated agent-handoffs-implementation-plan.md with enhanced implementation details
  - ✓ Added robust error handling and fallback mechanisms for handoff failures
  - ✓ Included tracing and debugging capabilities for handoff troubleshooting
  - ✓ Enhanced CONSOLIDATED_AGENT_HANDOFFS.md with detailed patterns and examples
  - ✓ Added sequential, decentralized handoff pattern as recommended by OpenAI
  - ✓ Created comprehensive testing strategies with example test cases
  - ✓ Updated TODO.md to track implementation progress
  - ✓ Aligned implementation plan with KISS/YAGNI/DRY principles

## MVP Priority (Version 1.0)

- [x] **Error Handling Decorator Enhancement**

  - **Target:** `/src/utils/decorators.py`
  - **Goal:** Support both sync and async functions in `with_error_handling`
  - **Tasks:**
    - ✓ Add synchronous function support
    - ✓ Improve type hints using TypeVar
    - ✓ Add comprehensive docstrings and examples
    - ✓ Ensure proper error message formatting
  - **PR:** Completed in #85

- [x] **Apply Error Handling Decorator to Flight Search Tools**

  - **Target:** `/src/agents/flight_search.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - ✓ Refactor `search_flights` to use the decorator
    - ✓ Refactor `_add_price_history` to use the decorator
    - ✓ Refactor `_get_price_history` to use the decorator
    - ✓ Refactor `search_flexible_dates` to use the decorator

- [x] **Apply Error Handling Decorator to Accommodations Tools**

  - **Target:** `/src/agents/accommodations.py`
  - **Goal:** Eliminate redundant try/except blocks
  - **Tasks:**
    - ✓ Refactor `search_accommodations` to use the decorator
    - ✓ Refactor `get_accommodation_details` to use the decorator
    - ✓ Create standalone tests to verify error handling

- [x] **Standardize MCP Client Pattern**

  - **Target:** `/src/mcp/base_mcp_client.py` and implementations
  - **Goal:** Create consistent patterns for all MCP clients
  - **Tasks:**
    - ✓ Define standard client factory interfaces
    - ✓ Centralize configuration validation logic
    - ✓ Implement consistent initialization patterns
    - ✓ Standardize error handling approach
  - **Follow-up Tasks:**
    - ✓ Fix circular import between base_mcp_client.py and memory_client.py
    - ✓ Apply factory pattern to all other MCP clients (weather, calendar, etc.)
    - ✓ Improve unit test infrastructure for MCP client testing

- [x] **Consolidate Dual Storage Pattern**

  - **Target:** `/src/utils/dual_storage.py`
  - **Goal:** Extract common persistence logic to avoid duplication
  - **Tasks:**
    - ✓ Create a `DualStorageService` base class
    - ✓ Implement standard persistence operations
    - ✓ Refactor existing services to use the base class
    - ✓ Add proper interface for both Supabase and Memory backends
    - ✓ Create comprehensive test suite with mocked dependencies
    - ✓ Implement isolated tests for generic class behavior
  - **PR:** Completed in #91
  - **Added:** Created comprehensive documentation in dual_storage_refactoring.md

- [x] Design UserApiKey table in Supabase with encryption fields:

  ```sql
  CREATE TABLE user_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    service VARCHAR(255) NOT NULL, -- 'google_maps', 'duffel_flights', etc.
    encrypted_dek BYTEA NOT NULL,  -- Encrypted data encryption key
    encrypted_key BYTEA NOT NULL,  -- API key encrypted with DEK
    salt BYTEA NOT NULL,           -- Salt for key derivation
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    rotation_due_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    UNIQUE(user_id, service)
  );
  ```

- [x] Create Pydantic models for API key management:

  ```python
  from pydantic import BaseModel, Field
  from typing import Optional
  from datetime import datetime

  class UserApiKeyCreate(BaseModel):
      service: str = Field(..., pattern="^[a-z_]+$")
      api_key: str = Field(..., min_length=1)
      description: Optional[str] = None

  class UserApiKeyResponse(BaseModel):
      id: str
      service: str
      description: Optional[str]
      created_at: datetime
      last_used_at: Optional[datetime]
      rotation_due_at: Optional[datetime]
      is_active: bool
  ```

- [x] Implement master key derivation with PBKDF2:

  ```python
  from cryptography.fernet import Fernet
  from cryptography.hazmat.primitives import hashes
  from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
  import base64, os

  def generate_master_key(user_secret: str, salt: Optional[bytes] = None):
      """Generate master key using PBKDF2 with high iteration count"""
      salt = salt or os.urandom(16)
      kdf = PBKDF2HMAC(
          algorithm=hashes.SHA256(),
          length=32,
          salt=salt,
          iterations=600000,  # High iteration count for security
      )
      key = base64.urlsafe_b64encode(kdf.derive(user_secret.encode()))
      return key, salt
  ```

- [x] Implement envelope encryption pattern:

  ```python
  def encrypt_api_key(api_key: str, user_secret: str):
      """Encrypt API key using envelope encryption"""
      # Generate Data Encryption Key (DEK)
      dek = Fernet.generate_key()

      # Generate Master Key from user secret
      master_key, salt = generate_master_key(user_secret)

      # Encrypt DEK with master key
      master_fernet = Fernet(master_key)
      encrypted_dek = master_fernet.encrypt(dek)

      # Encrypt API key with DEK
      dek_fernet = Fernet(dek)
      encrypted_key = dek_fernet.encrypt(api_key.encode())

      return encrypted_dek, encrypted_key, salt
  ```

- [x] Implement secure decryption:

  ```python
  def decrypt_api_key(encrypted_dek: bytes, encrypted_key: bytes,
                    salt: bytes, user_secret: str) -> str:
      """Decrypt API key using envelope encryption"""
      # Regenerate master key
      master_key, _ = generate_master_key(user_secret, salt)

      # Decrypt DEK with master key
      master_fernet = Fernet(master_key)
      dek = master_fernet.decrypt(encrypted_dek)

      # Decrypt API key with DEK
      dek_fernet = Fernet(dek)
      api_key = dek_fernet.decrypt(encrypted_key).decode()

      # Clear sensitive data from memory
      del dek
      del master_key

      return api_key
  ```

- [x] POST `/api/user/keys` - Store encrypted API keys (specification completed):

  ```python
  @router.post("/api/user/keys")
  async def create_api_key(
      key_data: UserApiKeyCreate,
      user: User = Depends(get_current_user),
      db: Database = Depends(get_db)
  ):
      # Validate key with service first
      is_valid = await validate_key_with_service(
          key_data.service,
          key_data.api_key
      )
      if not is_valid:
          raise HTTPException(400, "Invalid API key")

      # Encrypt using envelope encryption
      encrypted_dek, encrypted_key, salt = encrypt_api_key(
          key_data.api_key,
          user.secret_key
      )

      # Store encrypted data
      result = await db.execute(
          user_api_keys.insert().values(
              user_id=user.id,
              service=key_data.service,
              encrypted_dek=encrypted_dek,
              encrypted_key=encrypted_key,
              salt=salt,
              description=key_data.description,
              rotation_due_at=datetime.utcnow() + timedelta(days=90)
          )
      )

      # Clear sensitive data
      key_data.api_key = ""

      return {"id": result.inserted_primary_key[0]}
  ```

- [x] Create UserKeyProvider class (specification completed):

  ```python
  class UserKeyProvider:
      def __init__(self, redis_client: Redis):
          self.redis = redis_client
          self.cache_ttl = 300  # 5 minutes

      async def get_user_key(self, user_id: str, service: str) -> Optional[str]:
          # Check cache first
          cache_key = f"user_key:{user_id}:{service}"
          cached = await self.redis.get(cache_key)
          if cached:
              return cached

          # Fetch and decrypt from database
          key_data = await fetch_user_key(user_id, service)
          if not key_data:
              return None

          # Decrypt key
          api_key = decrypt_api_key(
              key_data.encrypted_dek,
              key_data.encrypted_key,
              key_data.salt,
              get_user_secret(user_id)
          )

          # Cache decrypted key with TTL
          await self.redis.setex(cache_key, self.cache_ttl, api_key)

          # Update last_used_at
          await update_key_usage(key_data.id)

          return api_key
  ```

- [x] Modify MCPManager.invoke to accept user context (specification completed):

  ```python
  async def invoke(self, server_type: str, method: str,
                  params: Dict[str, Any], user_id: Optional[str] = None):
      # Get user key if available
      if user_id:
          user_key = await self.key_provider.get_user_key(user_id, server_type)
          if user_key:
              params = {**params, "api_key": user_key}

      # Continue with MCP invocation
      return await self._invoke_internal(server_type, method, params)
  ```

- [x] Update tool imports:

  - ✓ Update `tripsage/tools/time_tools.py` to use `from agents import function_tool`
  - ✓ Update `tripsage/tools/memory_tools.py` to use `from agents import function_tool`
  - ✓ Update `tripsage/tools/webcrawl_tools.py` to use `from agents import function_tool`

- [x] Migrate remaining agent files:

  - ✓ Migrate `src/agents/budget_agent.py` → `tripsage/agents/budget.py`
  - ✓ Migrate `src/agents/itinerary_agent.py` → `tripsage/agents/itinerary.py`

- [x] Migrate remaining tool files:

  - ✓ Migrate `src/agents/planning_tools.py` → `tripsage/tools/planning_tools.py`

- [x] Migrate additional agent files:

  - ✓ Migrate `src/agents/travel_insights.py` → `tripsage/agents/travel_insights.py`
  - ✓ Migrate `src/agents/flight_booking.py` → `tripsage/tools/flight_booking.py`
  - ✓ Migrate `src/agents/flight_search.py` → `tripsage/tools/flight_search.py`

- [x] Migrate browser tools:

  - ✓ Migrate `src/agents/tools/browser/` → `tripsage/tools/browser/`
  - ✓ Update imports in `tripsage/tools/browser/tools.py` to use `from agents import function_tool`
  - ✓ Update imports in `tripsage/tools/browser_tools.py` to use `from agents import function_tool`

- [x] Update remaining imports:

  - ✓ Update all `from src.*` imports to `from tripsage.*`
  - ✓ Ensure consistent use of the `agents` module instead of `openai_agents_sdk`

- [x] Update imports in test files to use tripsage module

- [x] Create new `tests/` directory structure mirroring `tripsage/`
- [x] Create shared `conftest.py` with common fixtures

- [x] Create unit tests for MCPManager

  - [x] Test initialization and configuration
  - [x] Test invoke() method with various scenarios
  - [x] Test error handling and retries

- [x] Create unit tests for MCPClientRegistry

  - [x] Test wrapper registration
  - [x] Test wrapper retrieval
  - [x] Test dynamic loading

- [x] Create tests for core MCP wrappers

  - [x] Test Weather MCP wrapper
  - [x] Test Google Maps MCP wrapper
  - [x] Test Time MCP wrapper
  - [x] Test Supabase MCP wrapper
  - [x] Test method mapping
  - [x] Test parameter validation
  - [x] Test error handling

- [x] Create tests for Base MCP Wrapper
- [x] Create tests for exception hierarchy

- [x] Clean up duplicated files:

  - [x] Migrate key utilities from src/utils:
    - ✓ Deleted deprecated `src/utils/config.py`
    - ✓ Migrated `src/utils/decorators.py` functionality to `tripsage/utils/decorators.py`
    - ✓ Deleted `src/utils/error_decorators.py` (merged into decorators.py)
    - ✓ Deleted `src/utils/error_handling.py` (covered by new implementation)
  - [x] Complete remaining source directory cleanup
    - ✓ Deleted src/db/ (replaced by MCP approach)
    - ✓ Deleted src/mcp/ (refactored to mcp_abstraction and clients)
    - ✓ Deleted src/agents/ (migrated to tripsage)
    - ✓ Deleted src/utils/ (enhanced implementations in tripsage)
    - ✓ Deleted src/tests/ (obsolete tests)

- [x] Ensure no duplicate functionality exists

- [x] Frontend Architecture & Planning:

  - ✓ Conducted comprehensive research on Next.js 15, React 19, and shadcn/ui
  - ✓ Researched Vercel AI SDK v5 with streaming protocol
  - ✓ Analyzed MCP SDK integration patterns for TypeScript
  - ✓ Created comprehensive frontend specifications (frontend_specifications_v2.md)
  - ✓ Implemented Zod integration strategy (zod_integration_guide.md)
  - ✓ Created detailed frontend TODO list (TODO-FRONTEND.md)
  - ✓ Validated technology stack with latest documentation
  - ✓ Defined architecture patterns for AI-native interface
  - ✓ Established backend-only MCP interaction pattern
  - ✓ Designed secure BYOK (Bring Your Own Key) architecture
  - ✓ Updated TODO-FRONTEND.md with enhanced BYOK implementation

- [x] Database layer migration:

  - ✓ Created tripsage/models/db/ directory for essential business models
  - ✓ Migrated core entity models (User, Trip) with business validation
  - ✓ Implemented all essential database models:
    - ✓ Flight model with airline, booking status, and validation
    - ✓ Accommodation model with type, cancellation policy, and pricing
    - ✓ SearchParameters model with flexible parameter storage
    - ✓ TripNote model for note storage and management
    - ✓ PriceHistory model for tracking price changes
    - ✓ SavedOption model for storing travel options
    - ✓ TripComparison model for comparing trip alternatives
  - ✓ Implemented domain-specific Supabase tools in supabase_tools.py
  - ✓ Enhanced SupabaseMCPWrapper for database operations
  - ✓ Created tripsage/db/migrations/sql/ directory (exists as root migrations/)
  - ✓ Adapted run_migrations.py to use Supabase MCP's execute_sql
  - ✓ Created tripsage/db/migrations/neo4j/ for graph schema scripts
  - ✓ Implemented Neo4j initialization logic using Memory MCP
  - ✓ Added domain-specific tools in memory_tools.py for complex queries

- [x] **API Consolidation**

  - **Target:** `/tripsage/api/` directory (completed consolidation from `/api/` root directory)
  - **Goal:** Provide unified API implementation with modern FastAPI patterns
  - **Status:** ✅ Completed on May 20, 2025 (PR #91)
  - **Tasks:**
    - [x] Create and implement tripsage/api directory with FastAPI structure:
      - [x] Create endpoint groups by domain (users, trips, flights, etc.)
      - [x] Implement proper dependency injection with modern patterns
      - [x] Add comprehensive request/response models with Pydantic V2
      - [x] Migrate all routers from `/api/` to `/tripsage/api/`:
        - [x] Auth router with logout and user info endpoints
        - [x] Trips router with improved implementation
        - [x] Flights router with Pydantic V2 validation
        - [x] Accommodations router with service pattern
        - [x] Destinations router with proper dependencies
        - [x] Itineraries router with enhanced functionality
      - [x] Create and implement service layer:
        - [x] TripService with singleton pattern
        - [x] FlightService with proper abstraction
        - [x] AccommodationService with dependency injection
        - [x] DestinationService with proper error handling
        - [x] ItineraryService with time slot management
    - [x] API Improvements:
      - [x] Add OpenAPI documentation with enhanced descriptions
      - [x] Implement API versioning with path prefixes
      - [x] Add proper rate limiting with configurable limits
      - [x] Implement comprehensive logging with structured logs
      - [x] Add request validation with Pydantic V2
      - [x] Create comprehensive test suite for all API endpoints

- [x] Implement error handling and monitoring infrastructure (foundational):

  - **Target:** MCP error handling, structured logging, and OpenTelemetry tracing
  - **Goal:** Create standardized error handling and monitoring for all MCP interactions
  - **Completed Tasks:**
    - ✓ Refined custom MCP exception hierarchy with specific error types
    - ✓ Added MCPTimeoutError, MCPAuthenticationError, MCPRateLimitError, MCPNotFoundError
    - ✓ Enhanced MCPManager.invoke with structured logging
    - ✓ Implemented OpenTelemetry span creation with appropriate attributes
    - ✓ Created exception mapping logic for common error types
    - ✓ Added monitoring.py for OpenTelemetry configuration
    - ✓ Configured OpenTelemetryConfig in app_settings.py
    - ✓ Used existing FastAPI dependency injection patterns

- [x] Supabase MCP Integration: (Short-Term Phase)

  - **Target:** Database operations for TripSage's SQL data
  - **Goal:** Provide seamless integration with Supabase database
  - **Success Metrics:**
    - 99.9% uptime for database operations
    - <100ms average query response time
    - 100% schema validation coverage
    - 95%+ test coverage with integration tests
  - **Resources:**
    - **Server Repo:** <https://github.com/supabase/mcp-supabase>
    - **Supabase Docs:** <https://supabase.com/docs>
  - **Completed Tasks:**
    - ✓ Set up Supabase MCP server configuration with external MCP server architecture
    - ✓ Created SupabaseMCPWrapper with comprehensive external server integration
    - ✓ Implemented all 34 Supabase MCP database operations with method mapping
    - ✓ Fixed configuration recursion issues using object.__setattr__ pattern
    - ✓ Added proper environment variable handling with TRIPSAGE_MCP_SUPABASE_ prefix
    - ✓ Created ExternalMCPClient architecture for external server communication
    - ✓ Implemented stdio transport for reliable MCP protocol communication
    - ✓ Added comprehensive test suite with >15 test cases covering all scenarios
    - ✓ Created extensive configuration tests for SupabaseMCPConfig validation
    - ✓ Applied KISS principles for simple, maintainable external server integration
    - ✓ Documentation research: Pydantic V2, MCP architecture, OpenAI Agents patterns

- [x] Neo4j Memory MCP Integration: (Immediate Phase)

  - **Target:** Knowledge graph operations for trip planning and domain data
  - **Goal:** Implement persistent memory graph for travel domain knowledge
  - **Success Metrics:**
    - 95%+ successful graph operations
    - <200ms average query response time
    - Complete coverage of entity/relationship models
    - 90%+ test coverage for graph operations
  - **Resources:**
    - **Server Repo:** <https://github.com/neo4j-contrib/mcp-neo4j>
    - **Neo4j Docs:** <https://neo4j.com/docs/>
    - **Memory MCP Docs:** <https://neo4j.com/labs/claude-memory-mcp/>
  - **Completed Tasks:**
    - ✓ Configured Neo4j Memory MCP server
    - ✓ Created Neo4jMemoryMCPWrapper with standardized method mapping
    - ✓ Refactored `tripsage/tools/memory_tools.py` to use MCPManager
    - ✓ Implemented entity/relationship management functions
    - ✓ Added proper error handling with TripSageMCPError
    - ✓ Added model validation for all operations

- [x] Duffel Flights MCP Integration: (Short-Term Phase)

  - **Target:** Flight search and booking for travel planning
  - **Goal:** Enable comprehensive flight options with real-time pricing
  - **Success Metrics:**
    - 95%+ successful flight searches
    - <3 second average response time
    - Complete coverage of major global airlines
    - 90%+ test coverage with realistic flight scenarios
  - **Resources:**
    - **Server Repo:** <https://github.com/duffel/mcp-flights>
    - **Duffel API Docs:** <https://duffel.com/docs/api>
  - **Completed Tasks:**
    - ✓ Set up Duffel Flights MCP configuration
    - ✓ Created DuffelFlightsMCPWrapper with standardized method mapping
    - ✓ Refactored `tripsage/tools/flight_tools.py` to use MCPManager
    - ✓ Implemented offer and search functionality
    - ✓ Added proper error handling with TripSageMCPError
    - ✓ Added model validation for all operations

- [x] Airbnb MCP Integration: (Short-Term Phase)

  - **Target:** Accommodation search and booking capabilities
  - **Goal:** Enable comprehensive lodging options for travel planning
  - **Success Metrics:**
    - 90%+ successful accommodation searches
    - <5 second average response time
    - Accurate pricing and availability data
    - 90%+ test coverage for accommodation operations
  - **Resources:**
    - **Server Repo:** <https://github.com/openbnb/mcp-airbnb>
    - **API Reference:** <https://github.com/openbnb/openbnb-api>
  - **Completed Tasks:**
    - ✓ Configured Airbnb MCP server
    - ✓ Created AirbnbMCPWrapper with standardized method mapping
    - ✓ Refactored `tripsage/tools/accommodation_tools.py` to use MCPManager
    - ✓ Implemented listing search and details functionality
    - ✓ Added proper error handling with TripSageMCPError
    - ✓ Added model validation for all operations

- [x] Playwright MCP Integration: (Immediate Phase)

  - **Target:** Browser automation for complex travel workflows
  - **Goal:** Provide fallback mechanism for sites that block scrapers
  - **Success Metrics:**
    - 95%+ successful completion rate for authenticated workflows
    - <5 second average response time for cached operations
    - 90%+ test coverage with integration tests
    - Successful fallback handling for at least 5 major travel sites
  - **Resources:**
    - **Server Repo:** <https://github.com/executeautomation/mcp-playwright>
    - **Playwright Docs:** <https://playwright.dev/docs/intro>
  - **Tasks:**
    - [x] Configure Playwright MCP server with Python integration
      - ✓ Created PlaywrightMCPClient class in tripsage/tools/browser/playwright_mcp_client.py
      - ✓ Implemented JSON-RPC style client using httpx for async operations
      - ✓ Added proper connection pooling and timeout management
      - ✓ Integrated with MCP configuration system for settings
    - [x] Create browser automation toolkit
      - ✓ Added core browser operations (navigate, screenshot, click, fill)
      - ✓ Implemented content extraction methods (get_visible_text, get_visible_html)
      - ✓ Created agent-callable function tools in browser_tools.py
      - ✓ Used proper async/await patterns with context managers
    - [x] Implement proper error handling
      - ✓ Used @with_error_handling decorator for standardized error reporting
      - ✓ Created PlaywrightMCPError class for clear error categorization
      - ✓ Added comprehensive logging for operations and errors

- [x] Hybrid Web Crawling Integration: (Immediate-to-Short-Term Phase)

  - **Target:** Implement domain-optimized web crawling strategy
  - **Goal:** Maximize extraction performance and reliability for travel sites
  - **Success Metrics:**
    - 90%+ extraction success rate across all targeted travel sites
    - <4 seconds average response time for optimized domains
    - 95% accuracy in content extraction compared to manual collection
    - <15% fallback rate to browser automation
  - **Tasks:**
    - [x] Crawl4AI MCP Integration:
      - **Resources:**
        - **Server Repo:** <https://github.com/unclecode/crawl4ai>
        - **API Docs:** <https://github.com/unclecode/crawl4ai/blob/main/DEPLOY.md>
      - **Completed Tasks:**
        - ✓ Configured Crawl4AI MCP server with WebSocket and SSE support
        - ✓ Implemented in `tripsage/clients/webcrawl/crawl4ai_mcp_client.py`
        - ✓ Created comprehensive client methods for crawling, extraction, and Q&A
        - ✓ Implemented content-aware caching with appropriate TTLs
        - ✓ Added support for markdown, HTML, screenshots, PDFs, and JavaScript execution
        - ✓ Created comprehensive tests in `tests/clients/webcrawl/test_crawl4ai_mcp_client.py`
        - ✓ Added documentation in `docs/integrations/mcp-servers/webcrawl/crawl4ai_mcp_client.md`
        - ✓ Extended ContentType enum with JSON, MARKDOWN, HTML, BINARY types
    - [x] Firecrawl MCP Integration:
      - **Resources:**
        - **Server Repo:** <https://github.com/mendableai/firecrawl-mcp-server>
        - **API Docs:** <https://docs.firecrawl.dev/>
      - **Completed Tasks:**
        - ✓ Configured official Firecrawl MCP server from MendableAI
        - ✓ Implemented in `tripsage/clients/webcrawl/firecrawl_mcp_client.py`
        - ✓ Created comprehensive client methods for scraping, crawling, and extraction
        - ✓ Implemented content-aware caching with specialized TTLs for booking sites
        - ✓ Added structured data extraction, batch operations, and search capabilities
        - ✓ Optimized for booking sites with shorter cache TTLs (1 hour for dynamic pricing)
        - ✓ Created comprehensive tests for client functionality
        - ✓ Added proper error handling with @with_error_handling decorator
    - [x] Source Selection Logic:
      - ✓ Implemented domain-based routing in `tripsage/tools/webcrawl/source_selector.py`
        - Created WebCrawlSourceSelector class with configurable domain mappings
        - Added content-type based routing for optimal crawler selection
        - Implemented domain routing configuration in `mcp_settings.py`
        - Created example configuration documentation
      - ✓ Created unified abstraction layer in `tripsage/tools/webcrawl_tools.py`
        - Implemented `crawl_website_content` as the main unified interface
        - Added convenience functions for specific content types
        - Integrated with source selector and result normalizer
      - ✓ Documented domain-specific optimization strategy
    - [x] Result Normalization:
      - ✓ Created consistent output schema in `tripsage/tools/webcrawl/models.py`
        - Defined UnifiedCrawlResult Pydantic V2 model
        - Included all common fields across both crawlers
        - Added helper methods for timestamp and source checking
      - ✓ Implemented normalization logic in `tripsage/tools/webcrawl/result_normalizer.py`
        - Created normalize_firecrawl_output method
        - Created normalize_crawl4ai_output method
        - Handled error cases and edge conditions
      - ✓ Ensured unified interface regardless of underlying crawler
    - [x] Playwright MCP Fallback Integration:
      - ✓ Extended result normalizer with `normalize_playwright_mcp_output` method
        - Created normalization for Playwright MCP output
        - Handled browser-specific metadata (browser type, screenshots)
        - Integrated with UnifiedCrawlResult schema
      - ✓ Enhanced unified web crawl tool with fallback logic
        - Added Playwright MCP as fallback when primary crawlers fail
        - Implemented intelligent failure detection (error status, empty content, JS requirements)
        - Added `enable_playwright_fallback` parameter for control
        - Integrated proper error handling for both primary and fallback attempts
      - ✓ Refined WebCrawlSourceSelector for Playwright-only domains
        - Added CrawlerType.PLAYWRIGHT enum value
        - Defined default Playwright-only domains (social media, Google services)
        - Enhanced `select_crawler` method with `force_playwright` parameter
        - Added support for direct Playwright selection as primary crawler

- [x] Google Maps MCP Integration: (Immediate Phase)

  - **Target:** Location services and geographic data for trip planning
  - **Goal:** Enable high-quality geographic data for travel planning and routing
  - **Success Metrics:**
    - 99% geocoding success rate
    - <300ms average response time
    - Complete coverage of required location services
    - 90%+ test coverage for all implemented functions
  - **Resources:**
    - **Server Repo:** <https://github.com/googlemaps/mcp-googlemaps>
    - **API Docs:** <https://developers.google.com/maps/documentation>
  - **Tasks:**
    - [x] Set up Google Maps MCP configuration
      - ✓ Created GoogleMapsMCPConfig in tripsage/config/app_settings.py
      - ✓ Added proper configuration for server URL and API keys
      - ✓ Provided example configuration in example_mcp_settings.py
    - [x] Create GoogleMapsMCPClient implementation
      - ✓ Implemented in tripsage/clients/maps/google_maps_mcp_client.py
      - ✓ Created singleton client pattern with async/await support
      - ✓ Added content-aware caching with WebOperationsCache
      - ✓ Implemented comprehensive error handling with MCPError
    - [x] Created Google Maps MCP tools in tripsage/tools/googlemaps_tools.py
      - ✓ Implemented geocoding, reverse geocoding, place search
      - ✓ Added place details, directions, distance matrix
      - ✓ Created timezone and elevation tools
      - ✓ Added proper error handling with @with_error_handling decorator
    - [x] Added tests for Google Maps MCP client
      - ✓ Created comprehensive unit tests with mocked responses
      - ✓ Tested all API endpoints and caching behavior
      - ✓ Implemented error case testing
      - ✓ Created tests for singleton pattern and context management

- [x] Time MCP Integration: (Short-Term Phase)

  - **Target:** Timezone and time operations for global travel planning
  - **Goal:** Provide accurate time services for cross-timezone itineraries
  - **Success Metrics:**
    - 100% accuracy for timezone conversions
    - <100ms average response time
    - Support for all global timezones
    - 95%+ test coverage
  - **Resources:**
    - **Server Repo:** <https://github.com/anthropics/mcp-time>
    - **API Docs:** <https://worldtimeapi.org/api/>
  - [x] Configure Time MCP server
  - [x] Create time tools in `tripsage/tools/time_tools.py`
    - ✓ Implemented MCP client wrapper for the Time MCP
    - ✓ Updated tools to use MCPManager.invoke() instead of direct client calls
    - ✓ Added proper error handling with TripSageMCPError
  - [x] Implement timezone conversion and current time functionality
  - [x] Add tests for time-related operations

- [x] Weather MCP Integration: (Immediate Phase)

  - **Target:** Weather forecasting and historical data for trip planning
  - **Goal:** Enable weather-aware itinerary planning and recommendations
  - **Success Metrics:**
    - 95%+ availability for global weather data
    - <1 second average response time
    - Accurate forecasting for 7+ day window
    - 90%+ test coverage for API functions
  - **Resources:**
    - **Server Repo:** <https://github.com/szypetike/weather-mcp-server>
    - **API Docs:** <https://github.com/szypetike/weather-mcp-server#usage>
  - **Tasks:**
    - [x] Configure Weather MCP server
      - ✓ Created WeatherMCPConfig in tripsage/config/app_settings.py
      - ✓ Added configuration for server URL and API keys
      - ✓ Integrated with OpenWeatherMap API
    - [x] Create WeatherMCPClient implementation
      - ✓ Implemented in tripsage/clients/weather/weather_mcp_client.py
      - ✓ Created singleton client pattern with async/await support
      - ✓ Added content-aware caching with different TTLs (REALTIME, DAILY)
      - ✓ Implemented comprehensive error handling with MCPError
    - [x] Created weather tools in `tripsage/tools/weather_tools.py`
      - ✓ Updated existing weather tools to use new client
      - ✓ Implemented get_current_weather, get_forecast, get_travel_recommendation
      - ✓ Added get_destination_weather, get_trip_weather_summary tools
      - ✓ Maintained backward compatibility with existing tool interfaces
    - [x] Add tests for weather-related operations
      - ✓ Created comprehensive unit tests for WeatherMCPClient
      - ✓ Added tests for all API endpoints and caching behavior
      - ✓ Implemented isolated tests to avoid settings loading issues
      - ✓ Created tests for singleton pattern and error handling

- [x] Google Calendar MCP Integration: (Short-Term Phase)

  - **Target:** Calendar integration for trip planning and scheduling
  - **Goal:** Enable seamless addition of travel events to user calendars
  - **Success Metrics:**
    - 98%+ successful event creation/modification
    - <1 second average operation time
    - Complete support for all required calendar operations
    - 95%+ test coverage
  - **Resources:**
    - **Server Repo:** <https://github.com/googleapis/mcp-calendar>
    - **API Docs:** <https://developers.google.com/calendar/api/v3/reference>
  - ✓ Configure Google Calendar MCP server
  - ✓ Create calendar tools in `tripsage/tools/calendar_tools.py`
    - ✓ Created GoogleCalendarMCPWrapper with standardized method mapping
    - ✓ Refactored calendar_tools.py to use MCPManager for all MCP interactions
    - ✓ Added proper error handling with TripSageMCPError
  - ✓ Implement event creation and scheduling functionality
  - ✓ Add tests for calendar-related operations

- [x] WebSearchTool Integration with Caching (Issue #37):

  - **Target:** Implement caching for OpenAI Agents SDK WebSearchTool
  - **Goal:** Optimize performance and reduce API usage for web searches
  - **Status:** ✅ COMPLETED - Integration implemented and validated
  - **Resources:**
    - **OpenAI Agents SDK:** <https://openai.github.io/openai-agents-python/>
    - **Redis Client Docs:** <https://redis-py.readthedocs.io/en/stable/>
  - **Research Findings:**
    - WebSearchTool already implemented in TravelPlanningAgent and DestinationResearchAgent
    - Domain configurations differ appropriately between agents
    - Redis caching infrastructure exists but needs web-specific extensions
    - **Note:** OpenAI SDK's WebSearchTool does not support allowed_domains/blocked_domains
  - **Tasks:**
    - [x] Create WebOperationsCache class in `tripsage/utils/cache.py`:
      - ✓ Extended existing Redis caching with content-type awareness
      - ✓ Implemented TTL management based on content volatility
      - ✓ Added metrics collection for cache performance analysis
    - [x] Create CachedWebSearchTool wrapper in `tripsage/tools/web_tools.py`:
      - ✓ Wrapped WebSearchTool with identical interface for transparent integration
      - ✓ Implemented cache checking before API calls
      - ✓ Store results with appropriate TTL based on content type
    - [x] Update agent implementations:
      - ✓ Updated TravelPlanningAgent and DestinationResearchAgent to use wrapper
      - ✓ Updated TravelAgent to use CachedWebSearchTool instead of WebSearchTool
      - ✓ Removed domain configurations (not supported by OpenAI SDK)
    - [x] Add configuration settings:
      - ✓ Configured TTL settings in centralized configuration
      - ✓ Enabled runtime TTL adjustments without code changes
    - [x] Add comprehensive tests:
      - ✓ Created validation tests for code structure
      - ✓ Verified integration in both agents

- [x] **Redis MCP Integration**

  - **Target:** Redis MCP integration for standardized caching
  - **Goal:** Implement comprehensive Redis MCP-based caching system
  - **Status:** ✅ COMPLETED - PR created with complete implementation (May 21, 2025)
  - **Tasks:**
    - ✓ Complete Redis MCP client implementation in RedisMCPWrapper:
      - ✓ Implemented full RedisMCPClient with comprehensive Redis operations
      - ✓ Added support for key operations (get, set, delete)
      - ✓ Added support for list, set, and hash operations
      - ✓ Implemented pattern matching and key scanning
      - ✓ Created connection management with pooling and reconnection
      - ✓ Added metrics collection and sampling
    - ✓ Create comprehensive cache tools in cache_tools.py:
      - ✓ Implemented standardized caching functions using Redis MCP
      - ✓ Created cache decorators with content-type awareness
      - ✓ Added cache key generation utilities
      - ✓ Implemented TTL management based on content types
      - ✓ Added cache invalidation patterns
      - ✓ Created metrics collection with different time windows
    - ✓ Update web_tools.py to use new cache_tools:
      - ✓ Modified CachedWebSearchTool to use Redis MCP tools
      - ✓ Updated web_cached decorator to use Redis MCP
      - ✓ Standardized cache approach across web operations
    - ✓ Create comprehensive tests for Redis MCP:
      - ✓ Implemented thorough tests for all caching functionality
      - ✓ Added tests for cache decorators and key generation
      - ✓ Created tests for TTL management and content type detection
      - ✓ Added tests for cache statistics and metrics
    - ✓ Update TODO.md to reflect implementation progress
  - **Resources:**
    - **Redis MCP Server:** <https://github.com/redis/mcp-redis>
    - **Redis Docs:** <https://redis.io/docs/>
  - **PR:** #f269a43 (May 21, 2025)

- [x] Implement WebOperationsCache for Web Operations (Issue #38):

  - **Target:** Advanced caching system for TripSage web operations
  - **Goal:** Create a centralized, content-aware caching system for all web operation tools
  - **Status:** Implemented core functionality, requires integration testing
  - **Resources:**
    - **Redis Client Docs:** <https://redis-py.readthedocs.io/en/stable/>
    - **OpenAI Agents SDK:** <https://openai.github.io/openai-agents-python/>
  - **Tasks:**
    - [x] Implement WebOperationsCache Class in `tripsage/utils/cache.py`:
      - [x] Create `ContentType` enum with categories (REALTIME, TIME_SENSITIVE, DAILY, SEMI_STATIC, STATIC)
      - [x] Implement Redis integration using `redis.asyncio` for async compatibility
      - [x] Define configurable TTL settings for each content type
      - [x] Implement core cache methods (get, set, delete, invalidate_pattern)
      - [x] Create content-aware TTL logic that analyzes query and result patterns
      - [x] Implement `generate_cache_key` method for deterministic key generation
      - [x] Create singleton instance for application-wide use
    - [x] Implement Metrics Collection:
      - [x] Create metrics storage structure in Redis
      - [x] Add hit/miss counters with time windows (1h, 24h, 7d)
      - [x] Implement performance measurement for cache operations
      - [x] Create `get_stats` method for metrics retrieval
      - [x] Implement sampling for detailed metrics to reduce overhead
    - [x] Implement CachedWebSearchTool in `tripsage/tools/web_tools.py`:
      - [x] Create wrapper around OpenAI Agents SDK WebSearchTool
      - [x] Maintain identical interface for seamless integration
      - [x] Add caching with domain-aware cache keys
      - [x] Implement content type detection from search queries and results
    - [x] Create Web Caching Decorator:
      - [x] Implement `web_cached` decorator for other web operation functions
      - [x] Support async functions
      - [x] Add flexible content type detection
    - [x] Update Configuration Settings:
      - [x] Add TTL configuration to `app_settings.py`
      - [x] Create defaults for each content type (REALTIME: 100s, TIME_SENSITIVE: 5m, etc.)
      - [x] Make cache namespaces configurable
    - [x] Add Comprehensive Tests:
      - [x] Create unit tests for WebOperationsCache
      - [x] Add tests for CachedWebSearchTool
      - [x] Test metrics collection and retrieval
      - [x] Verify TTL logic with different content types
    - [x] Update Agent Implementations: (Completed)
      - [x] Replace WebSearchTool with CachedWebSearchTool in TravelPlanningAgent
        - Implementation complete using src/agents/travel_planning_agent.py
      - [x] Replace WebSearchTool with CachedWebSearchTool in DestinationResearchAgent
        - Implementation complete using src/agents/destination_research_agent.py
      - [x] Replace WebSearchTool with CachedWebSearchTool in TravelAgent
        - Updated src/agents/travel_agent.py to use cached version
    - [x] Implementation Timeline: (Completed)
      - [x] Phase 1: Core WebOperationsCache implementation
      - [x] Phase 2: Metrics and tool integration
      - [x] Phase 3: Testing and implementation
      - [x] Phase 4: Agent integration (Completed)
    - [x] Additional Considerations: (Implemented)
      - [x] Performance impact: Implemented sampling to minimize Redis overhead
      - [x] Fallback mechanism: Added robust error handling for Redis operations
      - [x] Cache size management: Implemented cache size estimation
      - [x] Analytics: Created WebCacheStats with hit/miss ratio tracking

- [x] Set up MCP configuration management system (foundational for all MCP integrations)

  - ✓ Created hierarchical Pydantic model structure for all MCP configurations
  - ✓ Implemented environment variable loading with nested delimiter support
  - ✓ Created dedicated configuration classes for each MCP type
  - ✓ Implemented singleton pattern for global settings access
  - ✓ Added comprehensive validation with Pydantic v2
  - ✓ Created example usage and client initialization patterns
  - ✓ Implemented in `tripsage/config/mcp_settings.py`

- [x] Integrate Playwright MCP (see Playwright MCP Integration)

  - ✓ Implemented PlaywrightMCPClient with core browser operations
  - ✓ Created agent-callable tools in browser_tools.py
  - ✓ Added proper error handling and logging

- [x] Remove legacy /mcp_servers/ directory (completed)

  - ✓ Removed incompatible legacy Node/JS approach
  - ✓ Cleaned up old configuration files

- [x] Reorganize scripts directory for better maintainability (completed)

  - ✓ Moved all test files from scripts/ to tests/integration/
    - ✓ Created subdirectories for different test types (mcp/, api/, database/)
    - ✓ Updated all imports to reflect new paths
  - ✓ Created subdirectories in scripts/ for better organization
    - ✓ mcp/ for MCP launcher scripts
    - ✓ database/ for database management scripts
    - ✓ startup/ for server start/stop scripts
    - ✓ verification/ for connection testing scripts
  - ✓ Added README.md documenting the new directory structure
  - ✓ Added `__init__.py` files to make directories proper Python packages
  - ✓ Updated documentation references to reflect new paths

- [x] Implement unified MCP launcher script (completed)

  - ✓ Created scripts/mcp/mcp_launcher.py with standardized launch mechanism
  - ✓ Supports all MCP server configurations
  - ✓ Added Node.js dependency checking with compatibility for all installation methods (nvm, fnm, volta, etc.)
  - ✓ Created comprehensive Node.js compatibility documentation
  - ✓ Fixed configuration attribute mapping to match actual MCPSettings structure
  - ✓ Added dependency checking functionality to warn users when Node.js is missing
  - ✓ Created scripts/mcp/mcp_launcher_simple.py for testing without configuration complexity

- [x] Create Docker-Compose orchestration (completed)

  - ✓ Created docker-compose.mcp.yml for MCP services
  - ✓ Defined service configurations and dependencies

- [x] Implement service registry pattern (completed)

  - ✓ Created dynamic MCP service management
  - ✓ Supports runtime discovery and configuration

- [x] Enhance MCP configuration with runtime/transport options (completed)

  - ✓ Added transport type configuration (stdio, http, ws)
  - ✓ Implemented runtime environment settings

- [x] Standardized on shell-script + Python-wrapper approach

  - ✓ Selected as the compatible strategy for FastMCP 2.0
  - ✓ Legacy Node/JS approach removed as incompatible

- [x] Implement unified abstraction layer for all MCP interactions:

  - ✓ Created Manager/Registry pattern with type-safe wrappers
  - ✓ Implemented standardized error handling with custom exceptions
  - ✓ Developed dependency injection support for FastAPI and similar frameworks
  - ✓ Created BaseMCPWrapper abstract class for consistent interface
  - ✓ Implemented MCPManager for centralized lifecycle management
  - ✓ Created MCPClientRegistry for dynamic wrapper registration
  - ✓ Added automatic registration of default wrappers on import
  - ✓ Provided examples for PlaywrightMCP, GoogleMapsMCP, and WeatherMCP
  - ✓ Core components reimplemented (2025-01-16):
    - ✓ BaseMCPWrapper with updated method signatures
    - ✓ MCPClientRegistry singleton implementation
    - ✓ MCPManager with configuration loading
    - ✓ Custom exception hierarchy under TripSageMCPError
  - ✓ Specific wrapper implementations (2025-01-16):
    - ✓ PlaywrightMCPWrapper with standardized method mapping
    - ✓ GoogleMapsMCPWrapper with comprehensive mapping for maps APIs
    - ✓ WeatherMCPWrapper with weather service method mapping
    - ✓ Automatic registration in registration.py
    - ✓ Example refactored tool (weather_tools_abstraction.py)

- [x] Create additional MCP wrappers for remaining clients:

  - [x] SupabaseMCPWrapper for database operations
  - [x] Neo4jMemoryMCPWrapper for knowledge graph operations
  - [x] DuffelFlightsMCPWrapper for flight search and booking
  - [x] AirbnbMCPWrapper for accommodation search
  - [x] FirecrawlMCPWrapper for web crawling
  - [x] Crawl4AIMCPWrapper for AI-powered web crawling
  - [x] TimeMCPWrapper for timezone operations
  - [x] GoogleCalendarMCPWrapper for calendar integration
  - [x] RedisMCPWrapper for caching operations
  - [x] CachedWebSearchToolWrapper for web search with caching

- [x] Update browser_tools.py to use PlaywrightMCPWrapper
- [x] Update googlemaps_tools.py to use GoogleMapsMCPWrapper
- [x] Update weather_tools.py to use WeatherMCPWrapper
- [x] Update flight_tools.py to use DuffelFlightsMCPWrapper
- [x] Update accommodation_tools.py to use AirbnbMCPWrapper
- [x] Update webcrawl_tools.py to use Firecrawl/Crawl4AI wrappers
- [x] Update time_tools.py to use TimeMCPWrapper
- [x] Update calendar_tools.py to use GoogleCalendarMCPWrapper
- [x] Update supabase_tools.py to use SupabaseMCPWrapper
- [x] Update memory_tools.py to use Neo4jMemoryMCPWrapper

- [x] Remove redundant implementations after external MCP integration

  - ✓ Deleted entire src/mcp/ directory
  - ✓ All functionality migrated to new abstraction layer

- [x] Ensure proper use of Pydantic V2 patterns in remaining MCP clients
- [x] Create proper factory patterns for all MCP clients
- [x] Standardize configuration across all clients
- [x] Migrate essential clients to tripsage/clients/ directory
- [x] Implement comprehensive test suite for each client

## Medium Priority

- [x] **Fix MCP Import Circularity**

  - **Target:** `/src/mcp/base_mcp_client.py` and `/src/utils/decorators.py`
  - **Goal:** Resolve circular imports between modules
  - **Tasks:**
    - ✓ Refactor decorators.py to remove dependency on memory_client
    - ✓ Extract error handling logic to prevent circular dependencies
    - ✓ Implement proper module initialization order
    - ✓ Add clear documentation about module dependencies
  - **PR:** Completed

- [x] **Improve MCP Client Testing**

  - **Target:** `/tests/mcp/` directory
  - **Goal:** Create robust testing infrastructure for MCP clients
  - **Tasks:**
    - ✓ Create reusable mocks for settings and cache dependencies
    - ✓ Implement test fixtures for standard MCP client testing
    - ✓ Create factories for generating test data
    - ✓ Achieve 90%+ test coverage for all MCP client code
  - **PR:** Completed
  - **Added:** Created comprehensive documentation in isolated_mcp_testing.md

- [x] **Simplify Tool Registration Logic**

  - **Target:** `/src/agents/base_agent.py`
  - **Goal:** Reduce verbosity in tool registration
  - **Tasks:**
    - ✓ Implement a generic `register_tool_group` method
    - ✓ Create a more declarative approach to tool registration
    - ✓ Add automatic tool discovery in specified modules

- [x] **Centralize Parameter Validation**

  - **Target:** MCP client implementations
  - **Goal:** Use Pydantic more consistently for validation
  - **Tasks:**
    - ✓ Define standard field validators for common patterns
    - ✓ Create base model classes for common parameter groups
    - ✓ Implement consistent validation messages

- [x] **Improve HTTP Client Usage**

  - **Target:** Client implementation files
  - **Goal:** Switch from `requests` to `httpx` per coding standards
  - **Tasks:**
    - [x] Identify all uses of the `requests` library (No active usage found in Python source code as of YYYY-MM-DD)
    - [N/A] Replace with async `httpx` client (Not applicable as no `requests` usage to replace)
    - [N/A] Implement proper connection pooling and timeouts (Not applicable)

- [x] Replace any pandas usage with polars (No pandas usage found in src)
- [x] Use pyarrow for columnar data operations (No pyarrow usage found; no immediate pandas/columnar processing to optimize with it)

- [x] Neo4j Database Improvements:

  - ✓ Standardized Neo4j query patterns through Memory MCP tools
  - ✓ Implemented proper transaction handling via MCP abstraction
  - ✓ Created Neo4j schema management system in tripsage/db/migrations/neo4j/
  - ✓ Ported constraint and index definitions from src/db/neo4j/migrations/
  - ✓ Implemented initialization logic using Memory MCP operations
  - ✓ Added domain-specific memory tools for complex entity relationships
  - ✓ Migrated domain schemas to appropriate tool schemas
  - ✓ Implemented proper error handling for Neo4j operations

- [x] Frontend Architecture & Planning:
  - ✓ Created comprehensive technology stack recommendations
  - ✓ Designed complete frontend architecture (docs/frontend/ARCHITECTURE.md)
  - ✓ Selected SOTA tech stack: Next.js 15.3, React 19, TypeScript 5.5, Tailwind CSS v4
  - ✓ Established Supabase Auth as authentication solution
  - ✓ Designed SSE-based real-time communication with Vercel AI SDK v5
  - ✓ Created phased implementation plan in TODO-FRONTEND.md
  - ✓ Defined secure API key management strategy (backend proxy pattern)
  - ✓ Updated frontend BYOK implementation to align with backend design

- [x] **API and Database Migrations**

  - **Target:** `/tripsage/api/` directory (completed consolidation from `/api/` root directory)
  - **Goal:** Provide unified API implementation with modern FastAPI patterns
  - **Status:** ✅ API consolidation completed on May 20, 2025 (PR #91), database migration in progress
  - **Tasks:**
    - [x] Create and implement tripsage/api directory with FastAPI structure:
      - [x] Create endpoint groups by domain (users, trips, flights, etc.)
      - [x] Implement proper dependency injection with modern patterns
      - [x] Add comprehensive request/response models with Pydantic V2
      - [x] Migrate all routers from `/api/` to `/tripsage/api/`:
        - [x] Auth router with logout and user info endpoints
        - [x] Trips router with improved implementation
        - [x] Flights router with Pydantic V2 validation
        - [x] Accommodations router with service pattern
        - [x] Destinations router with proper dependencies
        - [x] Itineraries router with enhanced functionality
      - [x] Create and implement service layer:
        - [x] TripService with singleton pattern
        - [x] FlightService with proper abstraction
        - [x] AccommodationService with dependency injection
        - [x] DestinationService with proper error handling
        - [x] ItineraryService with time slot management
    - [x] API Improvements:
      - [x] Add OpenAPI documentation with enhanced descriptions
      - [x] Implement API versioning with path prefixes
      - [x] Add proper rate limiting with configurable limits
      - [x] Implement comprehensive logging with structured logs
      - [x] Add request validation with Pydantic V2
      - [x] Create comprehensive test suite for all API endpoints
    - [ ] Implement database migration:
      - [x] Create tripsage/models/db/ for essential business models (User, Trip)
      - [x] Port validation logic to new Pydantic V2 models with field_validator
      - [ ] Replace repository patterns with MCP tool implementations
      - [ ] Adapt SQL migrations to use Supabase MCP apply_migration
      - [ ] Create Neo4j schema initialization scripts
      - [ ] Ensure consistent error handling through MCP abstraction
      - [ ] Remove direct database connection pooling (handled by MCPs)

- [x] FastAPI Implementation:
  - ✓ Created tripsage/api directory with modern FastAPI structure
  - ✓ Designed modular architecture with separation of concerns
  - ✓ Implemented core middleware components:
    - ✓ Authentication middleware with JWT and API key support
    - ✓ Rate limiting middleware with Redis support
    - ✓ Logging middleware with correlation IDs and structured logging
  - ✓ Created API endpoint groups by domain:
    - ✓ Auth endpoints (register, login, refresh token)
    - ✓ API key management endpoints (BYOK)
    - ✓ Health check endpoints
  - ✓ Implemented BYOK functionality:
    - ✓ Created secure API key management with envelope encryption
    - ✓ Implemented key rotation and validation
    - ✓ Added secure caching for decrypted keys
  - ✓ Added API improvements:
    - ✓ Custom OpenAPI documentation with examples
    - ✓ Comprehensive exception handling
    - ✓ Request validation with Pydantic V2
    - ✓ API versioning
  - ✓ Created comprehensive test suite:
    - ✓ Test fixtures for authentication and API key testing
    - ✓ Unit tests for API endpoints
    - ✓ Integration tests with mocked dependencies

## Low Priority

- [x] **Extract Common Service Patterns**

  - **Target:** Service modules in MCP implementations
  - **Goal:** Standardize service layer patterns
  - **Tasks:**
    - ✓ Define base service interfaces
    - ✓ Create standard patterns for service methods
    - ✓ Extract common logic to base classes

- [x] **Neo4j AuraDB API MCP Evaluation (Issue #39)**

  - **Target:** Neo4j operational management
  - **Goal:** Evaluate the need for programmatic management of Neo4j AuraDB instances
  - **Status:** Evaluated and recommended against implementation at this time
  - **Tasks:**
    - ✓ Evaluate the mcp-neo4j-cloud-aura-api server's capabilities
    - ✓ Analyze TripSage's operational needs for Neo4j management
    - ✓ Conduct security and complexity assessment
    - ✓ Provide recommendation for Issue #39
  - **Findings:**
    - TripSage uses Neo4j as a persistent knowledge graph with stable connections
    - The Neo4j Memory MCP already provides all needed application-level interactions
    - Administrative operations are better handled through Neo4j Aura's web interface
    - Dynamic instance management would add unnecessary complexity and security concerns
    - KISS/YAGNI principles suggest avoiding this integration until specific operational needs arise
  - **Recommendation:** Maintain as Post-MVP / Low Priority. Do not implement until clear operational needs emerge.

- [x] **Create Isolated Test Utilities**
  - **Target:** Test files and fixtures
  - **Goal:** Create reusable test fixtures independent of environment variables
  - **Tasks:**
    - ✓ Create portable test modules that don't depend on settings
    - ✓ Implement isolated test fixtures with proper mocking
    - ✓ Standardize mocking approach for database and MCP clients
    - ✓ Add comprehensive test coverage for abstract base classes

## Compliance Checklist for Each Task

For each completed task, ensure:

- [x] `ruff check --fix` & `ruff format .` pass cleanly
- [x] Imports are properly sorted
- [x] Type hints are complete and accurate
- [x] Tests cover the changes (aim for ≥90%)
- [x] No secrets are committed
- [x] File size ≤500 LoC, ideally ≤350 LoC
- [x] Code follows KISS/DRY/YAGNI/SIMPLE principles

## Progress Tracking

| Task                            | Status | PR  | Notes                                                                                          |
| ------------------------------- | ------ | --- | ---------------------------------------------------------------------------------------------- |
| Calendar Tools Refactoring      | ✅     | #87 | Applied error handling decorator pattern                                                       |
| Flight Search Refactoring       | ✅     | #88 | Applied error handling decorator to four methods                                               |
| Error Handling Tests            | ✅     | #88 | Created standalone tests for decorator functionality                                           |
| Accommodations Refactoring      | ✅     | #89 | Applied error handling decorator to two methods                                                |
| MCP Client Standardization      | ✅     | #90 | Implemented client factory pattern, improved error handling                                    |
| MCP Factory Pattern             | ✅     | #90 | Created standard factory interface + implementations for Time & Flights                        |
| MCP Error Classification        | ✅     | #90 | Added error categorization system for better error handling                                    |
| MCP Documentation               | ✅     | #90 | Added comprehensive README for MCP architecture                                                |
| Dual Storage Service            | ✅     | #91 | Created DualStorageService base class with standard CRUD operations                            |
| Trip Storage Service            | ✅     | #91 | Implemented TripStorageService with Pydantic validation                                        |
| Fix Circular Imports            | ✅     | #92 | Fixed circular imports in base_mcp_client.py and decorators.py                                 |
| Isolated Test Patterns          | ✅     | #93 | Created environment-independent test suite for dual storage services                           |
| Comprehensive Test Coverage     | ✅     | #93 | Added tests for abstract interfaces and error handling                                         |
| MCP Isolated Testing            | ✅     | #94 | Implemented isolated testing pattern for MCP clients                                           |
| MCP Testing Documentation       | ✅     | #94 | Created documentation for isolated MCP testing pattern                                         |
| Tool Registration Logic         | ✅     | #95 | Simplified tool registration with automatic discovery                                          |
| Parameter Validation            | ✅     | #95 | Centralized parameter validation with Pydantic base models                                     |
| Service Pattern Extraction      | ✅     | #95 | Extracted common service patterns for MCP implementations                                      |
| Codebase Restructuring - Part 1 | ✅     | -   | Updated tool imports, migrated all agent files and tools                                       |
| Browser Tools Migration         | ✅     | -   | Updated browser tools with correct imports and tools registration                              |
| External MCP Server Strategy    | ✅     | -   | Completed evaluation of MCP servers and established hybrid approach                            |
| Playwright MCP Integration      | ✅     | -   | Implemented core client and agent-callable tools                                               |
| Crawl4AI MCP Integration        | ✅     | -   | Implemented client with WebSocket/SSE support, caching, and comprehensive tests                |
| Firecrawl MCP Integration       | ✅     | -   | Implemented client with specialized booking site optimization and caching                      |
| Hybrid Web Crawl Schema         | ✅     | -   | Created UnifiedCrawlResult model for consistent output across crawlers                         |
| Result Normalizer               | ✅     | -   | Implemented normalize methods for both Firecrawl and Crawl4AI outputs                          |
| Source Selection Logic          | ✅     | -   | Implemented domain routing and content-type based crawler selection                            |
| Unified Crawl Interface         | ✅     | -   | Created crawl_website_content with automatic crawler selection                                 |
| Playwright MCP Fallback         | ✅     | -   | Enhanced hybrid crawling with Playwright fallback and direct selection                         |
| Playwright Result Normalizer    | ✅     | -   | Added normalize_playwright_mcp_output for browser-based crawling                               |
| Playwright-only Domains         | ✅     | -   | Added support for direct Playwright selection for specific domains                             |
| Google Maps MCP Integration     | ✅     | -   | Implemented GoogleMaps MCP client wrapper and refactored googlemaps_tools.py to use MCPManager |
| Time MCP Integration            | ✅     | -   | Implemented Time MCP client wrapper and refactored time_tools.py to use MCPManager             |
| WebSearchTool Caching           | ✅     | -   | Implemented CachedWebSearchTool wrapper with content-aware caching                             |
| MCP Abstraction Layer           | ✅     | -   | Implemented Manager/Registry pattern with type-safe wrappers                                   |
| Specific MCP Wrappers           | ✅     | -   | Implemented Supabase, Neo4j Memory, Duffel Flights, and Airbnb wrappers                        |
| Backend BYOK Architecture       | ✅     | -   | Created comprehensive database schema and encryption design with PBKDF2 + Fernet               |
| Frontend BYOK Architecture      | ✅     | -   | Designed secure key management UI with auto-clear and client-side validation                   |
| Frontend-Backend BYOK Alignment | ✅     | -   | Aligned frontend and backend implementations with comprehensive documentation                  |
| Frontend Architecture v2        | ✅     | -   | Designed state-of-the-art architecture with Next.js 15, React 19, and AI-centric features      |
| Technology Stack v2             | ✅     | -   | Updated tech stack recommendations with latest stable versions and justifications              |
| Frontend Implementation Plan v2 | ✅     | -   | Created comprehensive 20-week phased implementation plan with code examples                    |
| Gap Analysis & Recommendations  | ✅     | -   | Identified gaps (offline support, PWA, i18n) and provided future enhancement roadmap           |
| MCP Server Strategy Decision    | ✅     | -   | Standardized on shell-script + Python-wrapper approach                                         |
| Legacy MCP Directory Removal    | ✅     | -   | Removed /mcp_servers/ directory                                                                |
| Unified MCP Launcher            | ✅     | -   | Created scripts/mcp_launcher.py                                                                |
| Docker-Compose MCP              | ✅     | -   | Created docker-compose.mcp.yml                                                                 |
| MCP Service Registry            | ✅     | -   | Implemented dynamic service management                                                         |
| Enhanced MCP Config             | ✅     | -   | Added runtime/transport configuration                                                          |