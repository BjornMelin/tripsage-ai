# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TripSage is an AI-powered travel planning system that seamlessly integrates flight, accommodation, and location data from multiple sources while storing search results in a dual-storage architecture (Supabase + knowledge graph memory). The system optimizes travel plans against budget constraints by comparing options across services, tracking price changes, and building a persistent knowledge base of travel relationships and patterns across sessions.

## Technical Architecture

### Dual Storage Architecture

#### Supabase Database Configuration

**Project Name:** tripsage_planner

**Schema Naming Conventions:**

- Use snake_case for all tables and columns (PostgreSQL standard)
- Tables should be lowercase with underscores separating words
- Foreign keys should use the singular form of the referenced table with \_id suffix
- Include created_at and updated_at timestamps on all tables
- Add appropriate comments to tables and complex columns

**Tables Schema:**

- trips
- flights
- accommodations
- transportation
- itinerary_items
- users
- search_parameters
- price_history
- trip_notes
- saved_options
- trip_comparison

#### Knowledge Graph Strategy

The TripSage system utilizes two distinct knowledge graphs:

1. **Travel Domain Knowledge Graph**

   - Stores travel-specific information (destinations, accommodations, etc.)
   - Used by the application to make travel recommendations

2. **Project Meta-Knowledge Graph** (Memory MCP)
   - Stores information about the TripSage system itself
   - Used by Claude to maintain project context across conversations

## Tool Integration Strategy

### MCP Servers & Tools Reference

- `github.*` → GitHub MCP Server (repo, PR, topics, merges)
- `git.*` → Git MCP Server (local clone, commit, pull, push)
- `seq.*` → Sequential-Thinking MCP Server (plan, reflect, gate next step)
- `mem.*` → Memory MCP Server (write, read, update knowledge graph)
- Travel-specific servers (flights-mcp, airbnb-mcp, google-maps-mcp)
- Web search servers (linkup-mcp, firecrawl-mcp)
- Database servers (supabase-mcp)
- Browser automation (playwright-mcp)
- Time management (time-mcp)

### MCP Tool Selection Priority

1. Travel-specific MCP servers (flights-mcp, airbnb-mcp, google-maps-mcp)
2. Web search and research tools (linkup-mcp, firecrawl-mcp)
3. Database tools (supabase-mcp, memory-mcp)
4. Browser automation (playwright-mcp) - only when specialized tools insufficient
5. Time management tools (time-mcp) - for timezone and scheduling assistance
6. Reasoning tools (sequentialthinking-mcp) - for complex planning optimization

### Specific Tool Usage Guidelines

#### Web Search Tools

**Linkup Search Tool (search-web):**

- Use as the default web search tool for most information needs
- Use "standard" depth parameter for straightforward queries
- Use "deep" depth parameter for complex queries requiring comprehensive analysis
- Handle one specific information need per search query for optimal results

**Firecrawl Tools:**

- Reserve for specialized needs that Linkup cannot efficiently address
- Use `firecrawl_scrape` for detailed extraction from specific webpages
- Use `firecrawl_map` for discovering multiple related URLs from a starting point
- Use `firecrawl_crawl` for systematic exploration of entire websites or sections
- Use `firecrawl_deep_research` for comprehensive analysis of complex topics

#### Memory Knowledge Graph Tools

Use memory MCP for maintaining contextual information across sessions:

- `read_graph` to initialize context at start of conversation
- `search_nodes` to find relevant previous trip patterns
- `open_nodes` to retrieve detailed information on specific entities
- `create_entities` to add new travel concepts discovered through research
- `create_relations` to connect entities with semantic relationships
- `add_observations` to enhance existing knowledge with new details
- Start each session with knowledge retrieval, end with knowledge update

#### Sequential Thinking Application

Use sequential thinking for complex optimization problems:

- Multi-city route optimization
- Budget allocation across different travel components
- Trade-off analysis between convenience, cost, and quality
- Identifying non-obvious cost-saving opportunities
- Planning complex itineraries with multiple constraints

#### Playwright Usage Guidelines

Only use Playwright MCP tools when:

- Dedicated travel MCP tools cannot access needed information
- Dynamic content requires browser interaction
- Comparison across multiple non-API travel sites is necessary
- Checking availability that requires form submission

When using Playwright, follow this sequence:

1. `playwright_navigate` to travel site
2. `playwright_fill`/`playwright_click` to input search parameters
3. `playwright_get_visible_text`/`playwright_get_visible_html` to extract results
4. Parse results and store in dual storage architecture

#### Time Management Tools

Use time MCP tools for:

- Converting flight times between timezones: `convert_time`
- Calculating local arrival times: `get_current_time`
- Determining optimal booking times based on timezone differences
- Planning itineraries across different time zones

### Optimization Strategies

- Always search with flexibility on dates when allowed
- Consider nearby airports or alternative accommodations
- Present trade-offs between convenience and cost
- Identify package deals across services
- Compare direct bookings vs. aggregator prices
- Suggest money-saving alternatives for each category

## Git & GitHub Workflow

### Ground Rules

- Use the existing SSH remote for every Git operation
- Never delete the `dev` branch; assume `main` and `dev` are protected
- Log every meaningful action to memory
- Each step must succeed before the next (`seq.next_step` as guard)

### Branch Strategy

- `main` - Production branch, protected
- `dev` - Development branch, protected
- Feature branches - Create from `dev`, name as `feature/descriptive-name`
- Fix branches - Create from `dev`, name as `fix/issue-description`

### Conventional Commits

Always use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Types:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: A code change that neither fixes a bug nor adds a feature
- `perf`: A code change that improves performance
- `test`: Adding missing tests or correcting existing tests
- `build`: Changes that affect the build system or external dependencies
- `ci`: Changes to CI configuration files and scripts

### GitHub Workflow

#### Repository Creation

```
github.create_repo
  name: "<repo-name>"
  private: true
  description: "<SEO-rich description>"
  topics: ["ai-agent", "mcp", "automation", ...]
```

#### Pull Request Process

```
github.create_pull_request
  title: "Merge dev into main – initial release"
  body: "<bullet-list of completed work>"
  base: "main"
  head: "dev"
```

```
github.add_comment
  pr_number: ${github.create_pull_request.number}
  comment: "### Self-review\n- [x] CI passes\n- [x] Accurate description\n- [x] No secrets committed"
```

```
github.merge_pull_request
  pr_number: ${github.create_pull_request.number}
  method: "merge"
```

#### Local Git Sync

```
git.fetch origin
git.pull origin main
git.pull origin dev
```

#### Memory Persistence

```
mem.write
  key: "release-<version>"
  value: {
    merged_sha: "${github.merge_pull_request.sha}",
    pr: "${github.create_pull_request.html_url}",
    date: "<ISO8601>"
  }
```

## Coding & Style Guidelines

### Python Standards

- Follow **PEP 8** and **PEP 257** guidelines
- Use **ruff** formatter and linting
- Always ensure ruff formatting and linting passes before committing changes
- Include full type hints throughout all code

### Documentation Standards

- Use **Google style** docstrings with module/class/function doc blocks
- Example:

  ```python
  def function_name(param1: type, param2: type) -> return_type:
      """Short description of function.

      More detailed description of function.

      Args:
          param1: Description of param1
          param2: Description of param2

      Returns:
          Description of return value

      Raises:
          ExceptionType: When and why this exception is raised
      """
  ```

### Logging Practices

- Use **lazy logging** to avoid string formatting overhead:

  ```python
  # CORRECT - string formatting happens only if debug is enabled
  logger.debug("Message with %s and %d", string_var, int_var)

  # INCORRECT - string formatting happens regardless of log level
  logger.debug(f"Message with {string_var} and {int_var}")
  ```

### Code Structure

- Keep files to a **maximum of 300 lines** when possible
- Limit functions to **50 lines or less** when feasible
- Use meaningful variable and function names

### Python Best Practices

- Use `uv` for Python virtual environment management and package installation

  ```bash
  # Create virtual environment
  uv venv

  # Install dependencies
  uv pip install -r requirements.txt

  # Add new package
  uv pip install package_name
  ```

- Use Pydantic for data validation, settings management, and serialization/deserialization

  ```python
  from pydantic import BaseModel, Field

  class TravelRequest(BaseModel):
      destination: str
      start_date: date
      end_date: date
      budget: float = Field(gt=0)
      travelers: int = Field(gt=0)
  ```

- Prefer tuple unpacking over index access where appropriate
- Use list/dict/set comprehensions for clarity and performance
- Prefer context managers (`with` statements) for resource management
- Use pathlib instead of os.path for file operations
- Follow Python's Zen (PEP 20) - `import this`
- Employ appropriate error handling with specific exceptions
- Use `if __name__ == "__main__":` pattern for executable scripts
- Leverage property decorators over getters/setters
- Favor composition over inheritance when appropriate

### Testing Standards

- Write unit tests for all new functionality
- Aim for high test coverage, especially for critical paths
- Use pytest as the testing framework
- Implement fixture patterns for test setup and teardown
- Include both positive and negative test cases
- Mock external dependencies for isolation

### PostgreSQL Guidelines

- Use explicit schema references in queries
- Create appropriate indexes for query optimization
- Employ parameterized queries to prevent SQL injection
- Implement row-level security policies for multi-tenant data
- Use transactions appropriately to maintain data integrity
- Keep DDL migrations idempotent and reversible
- Follow appropriate normalization practices
- Use constraints (CHECK, UNIQUE, FOREIGN KEY) to enforce data integrity
- Leverage PostgreSQL-specific features like JSONB, arrays, and GIN indexes where appropriate
- Document all database objects with comments
- Implement proper connection pooling in application code

### Design Principles

- **KISS** (Keep It Simple, Stupid) - Simplicity should be a key goal
- **DRY** (Don't Repeat Yourself) - Avoid code duplication
- **YAGNI** (You Aren't Gonna Need It) - Don't add functionality until necessary
- **SOLID**:
  - Single Responsibility Principle
  - Open/Closed Principle
  - Liskov Substitution Principle
  - Interface Segregation Principle
  - Dependency Inversion Principle
- **WYSIWYG** (What You See Is What You Get) - Code should be clear and predictable
- Do not over-engineer solutions

## Standardized Response Formats

The system follows structured response formats for different stages of the travel planning process, including:

- Initial Welcome Response
- Information Gathering Responses
- Search Acknowledgment Response
- Results Presentation Structure
- Exploration Options Format
- Error Response Format
- Booking Confirmation Format

## Agent Development Guidelines

### Workflows vs. Agents

In TripSage, we distinguish between two types of agentic systems:

- **Workflows:** Systems where LLMs and tools follow predefined code paths
- **Agents:** Systems where LLMs dynamically direct processes and tool usage

### Pattern Selection Framework

Choose the simplest effective pattern for each task:

1. **Single Augmented LLM Call** (First Choice)

   - For straightforward tasks with clear inputs and outputs
   - When the task doesn't require multiple steps or complex reasoning
   - Example: Generating destination descriptions or simple budget calculations

2. **Workflow Patterns** (Second Choice)

   - For predictable, decomposable tasks with known steps
   - When consistency and reliability are critical
   - Examples by workflow type:
     - **Prompt Chaining:** Sequential tasks like generating an itinerary outline, then expanding it
     - **Routing:** Directing different travel queries (flight search, accommodation, activities) to specialized handlers
     - **Parallelization:** Searching multiple sources simultaneously, or evaluating multiple travel options

3. **Autonomous Agent** (Last Resort)
   - For complex, unpredictable tasks requiring dynamic planning and tool use
   - When flexibility and model-driven decision-making are essential
   - Example: Complex multi-city trip planning with changing constraints

### Testing and Debugging Practices

1. **Transparent Reasoning**

   - Always include reasoning steps in agent prompts
   - Log the agent's thought process at each decision point
   - Use structured output formats to make reasoning explicit

2. **Modular Testing**

   - Test individual components before combining them
   - Create unit tests for each tool and prompt
   - Develop scenario-based tests for common travel planning flows

3. **Performance Metrics**

   - Track success rate on travel planning tasks
   - Measure latency, token usage, and cost
   - Evaluate user satisfaction and task completion rates

4. **Common Failure Modes**
   - Tool selection errors: Agent choosing inappropriate tools
   - Hallucination in travel details: Check factual accuracy against sources
   - Planning loops: Detect and break cycles with maximum iteration limits
   - Incomplete task execution: Verify all user requirements were addressed

### Error Handling and Recovery

1. **Proactive Error Detection**

   - Implement validation checks on all tool inputs and outputs
   - Verify budget calculations and timeline consistency
   - Cross-check critical travel details (dates, locations, availability)

2. **Graceful Degradation**

   - Fall back to simpler patterns when complex ones fail
   - Provide partial results when complete results aren't possible
   - Clearly communicate limitations to users

3. **Self-Correction Mechanisms**

   - Implement reflection cycles to evaluate and improve outputs
   - Allow agents to revise recommendations based on new information
   - Use evaluator-optimizer patterns for iterative refinement

4. **Human Feedback Integration**
   - Design clear checkpoints for human approval
   - Provide intervention mechanisms for correcting agent mistakes
   - Learn from user corrections to improve future performance

### Core Agent Design Principles

1. **Simplicity First**

   - Start with the simplest solution and add complexity only when necessary
   - Prefer fixed workflows for predictable tasks
   - Use autonomous agents sparingly and only for genuinely complex tasks

2. **Transparency Always**

   - Make agent reasoning visible and explainable
   - Document all tool capabilities and limitations
   - Provide clear indications when agents are uncertain

3. **Careful Tool Design**

   - Create clear, well-documented tool interfaces
   - Include examples in tool documentation
   - Design tools to be robust against invalid inputs
   - Test tools independently before integrating with agents

4. **Appropriate Guardrails**

   - Implement budget constraints as hard limits
   - Add safety checks for critical operations
   - Set reasonable time and resource limits
   - Include approval steps for high-impact actions

5. **Empirical Evaluation**

   - Test with diverse, realistic travel scenarios
   - Measure performance against baseline methods
   - Continuously improve based on real-world feedback
   - Document successful patterns for reuse

6. **Modular, Composable Architecture**
   - Build small, focused components
   - Design for reuse and combination
   - Maintain clean interfaces between components
   - Avoid tight coupling between agents and tools

## OpenAI Agents SDK Implementation Guidelines

TripSage uses the OpenAI Agents SDK for building agentic workflows. The following guidelines ensure consistent, maintainable, and effective implementation.

### Installation and Setup

```bash
# Install using uv
uv pip install openai-agents

# Set environment variable (never store API keys in code)
export OPENAI_API_KEY=sk-...
```

- Create a dedicated `agents` module in the project structure
- Use environment variables for API keys and configuration
- Configure tracing based on environment (enabled in development, configurable in production)

### Agent Architecture

1. **Hierarchical Structure**

   ```python
   from agents import Agent, handoff

   # Main orchestrator agent
   travel_agent = Agent(
       name="Travel Planning Agent",
       instructions="You are a comprehensive travel planning assistant...",
       handoffs=[flight_agent, accommodation_agent, activity_agent, budget_agent]
   )

   # Specialized sub-agents
   flight_agent = Agent(
       name="Flight Agent",
       instructions="You specialize in finding optimal flights...",
       tools=[search_flights, compare_prices, check_availability]
   )
   ```

2. **Agent Responsibilities**

   - **Travel Planning Agent**: Main orchestrator, manages overall planning
   - **Flight Agent**: Flight search and booking recommendations
   - **Accommodation Agent**: Hotel and rental searches and recommendations
   - **Activity Agent**: Local activities and attractions
   - **Budget Agent**: Budget optimization and allocation

3. **Model Selection**
   - Use `gpt-4` for complex reasoning tasks (main agent, budget optimization)
   - Use `gpt-3.5-turbo` for simpler, well-defined tasks (data extraction, formatting)
   - Set temperature to `0.2` for predictable, accurate responses
   - Set temperature to `0.7-0.9` for creative suggestions (activity ideas)

### Tool Implementation

1. **Function Tool Design**

   ```python
   from pydantic import BaseModel
   from typing import List, Optional
   from agents import function_tool

   class FlightSearchParams(BaseModel):
       origin: str
       destination: str
       departure_date: str
       return_date: Optional[str] = None
       max_price: Optional[float] = None
       passengers: int = 1

   @function_tool
   async def search_flights(params: FlightSearchParams) -> str:
       """Search for available flights based on user criteria.

       Args:
           params: The flight search parameters including origin, destination,
                  dates, price constraints, and number of passengers.

       Returns:
           A formatted string containing flight options or an error message.
       """
       # Implementation that accesses flight APIs
       # Store results in Supabase and knowledge graph
       pass
   ```

2. **Tool Guidelines**

   - Use `@function_tool` for automatic schema generation
   - Create Pydantic models for all tool inputs
   - Write comprehensive docstrings (Google style) for auto-documentation
   - Implement async functions for external API calls
   - Return clear, structured error messages
   - Include logging for debugging
   - Ensure tools store data in both Supabase and knowledge graph when appropriate

3. **Error Handling**

   ```python
   @function_tool
   async def search_flights(params: FlightSearchParams) -> str:
       try:
           # Call external flight API
           results = await flight_api.search(params.dict())

           # Store in Supabase
           await supabase.table("flights").insert(results)

           # Update knowledge graph
           await memory_client.create_entities(...)

           return format_flight_results(results)

       except FlightAPIError as e:
           logger.error(f"Flight API error: {e}")
           return f"Unable to search flights: {str(e)}"
       except Exception as e:
           logger.exception("Unexpected error in flight search")
           return "An unexpected error occurred during flight search"
   ```

### Handoff Implementation

1. **Basic Handoffs**

   ```python
   from agents import Agent, handoff
   from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX

   flight_agent = Agent(
       name="Flight Agent",
       instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou specialize in flight search..."
   )

   budget_agent = Agent(
       name="Budget Agent",
       instructions=f"{RECOMMENDED_PROMPT_PREFIX}\nYou specialize in budget optimization..."
   )

   travel_agent = Agent(
       name="Travel Planning Agent",
       instructions="You orchestrate the travel planning process...",
       handoffs=[flight_agent, budget_agent]
   )
   ```

2. **Handoff with Input Data**

   ```python
   from pydantic import BaseModel
   from agents import handoff, RunContextWrapper

   class BudgetOptimizationData(BaseModel):
       total_budget: float
       allocation_request: str
       priorities: list[str]

   async def on_budget_handoff(ctx: RunContextWrapper[None], input_data: BudgetOptimizationData):
       # Log the budget request
       # Preload relevant data
       pass

   budget_handoff = handoff(
       agent=budget_agent,
       on_handoff=on_budget_handoff,
       input_type=BudgetOptimizationData
   )

   travel_agent = Agent(
       name="Travel Planning Agent",
       handoffs=[flight_agent, budget_handoff]
   )
   ```

3. **Input Filtering**

   ```python
   from agents.extensions import handoff_filters

   # Remove previous tool calls from history when handing off
   filtered_handoff = handoff(
       agent=accommodation_agent,
       input_filter=handoff_filters.remove_all_tools
   )
   ```

### Guardrail Implementation

1. **Input Guardrails**

   ```python
   from pydantic import BaseModel
   from agents import Agent, GuardrailFunctionOutput, input_guardrail, RunContextWrapper

   class BudgetCheckOutput(BaseModel):
       is_within_reasonable_range: bool
       reasoning: str

   budget_check_agent = Agent(
       name="Budget Check",
       instructions="Check if the budget request is reasonable for the trip",
       output_type=BudgetCheckOutput
   )

   @input_guardrail
   async def budget_check_guardrail(
       ctx: RunContextWrapper[None],
       agent: Agent,
       input: str | list
   ) -> GuardrailFunctionOutput:
       result = await Runner.run(budget_check_agent, input, context=ctx.context)

       return GuardrailFunctionOutput(
           output_info=result.final_output,
           tripwire_triggered=not result.final_output.is_within_reasonable_range
       )

   travel_agent = Agent(
       name="Travel Planning Agent",
       input_guardrails=[budget_check_guardrail]
   )
   ```

2. **Output Guardrails**

   ```python
   from pydantic import BaseModel
   from agents import output_guardrail, GuardrailFunctionOutput

   class TravelPlanOutput(BaseModel):
       itinerary: str
       budget_allocation: dict

   class BudgetCheckOutput(BaseModel):
       is_within_budget: bool
       reasoning: str

   @output_guardrail
   async def budget_constraint_guardrail(
       ctx: RunContextWrapper,
       agent: Agent,
       output: TravelPlanOutput
   ) -> GuardrailFunctionOutput:
       # Check if budget allocation exceeds total budget
       total = sum(output.budget_allocation.values())
       is_within_budget = total <= ctx.context.get("total_budget", float("inf"))

       return GuardrailFunctionOutput(
           output_info={"is_within_budget": is_within_budget},
           tripwire_triggered=not is_within_budget
       )
   ```

### Tracing and Debugging

1. **Basic Tracing Configuration**

   ```python
   from agents import Agent, Runner, trace

   # Named trace for the entire workflow
   with trace("TripSage Planning Workflow"):
       initial_result = await Runner.run(travel_agent, user_query)
       refinement_result = await Runner.run(travel_agent, f"Refine this plan: {initial_result.final_output}")
   ```

2. **Custom Spans**

   ```python
   from agents.tracing import custom_span

   async def search_and_book():
       with custom_span("flight_search", {"query": flight_query}):
           # Flight search logic
           pass
   ```

3. **Sensitive Data Protection**

   ```python
   from agents import Agent, Runner, RunConfig

   # Don't include sensitive data in traces
   config = RunConfig(trace_include_sensitive_data=False)
   result = await Runner.run(agent, input, run_config=config)
   ```

4. **Debugging Strategy**
   - Review traces in OpenAI dashboard during development
   - Add detailed custom spans for critical operations
   - Use consistent workflow/span naming for easier filtering
   - Implement a custom trace processor for error alerting

### Testing and Deployment

1. **Testing Strategy**

   ```python
   import pytest
   from unittest.mock import AsyncMock, patch
   from agents import Agent, Runner

   @pytest.fixture
   def mock_flight_api():
       with patch("travel.apis.flight_api") as mock:
           mock.search = AsyncMock(return_value=[{"flight_id": "123", "price": 299.99}])
           yield mock

   async def test_flight_agent(mock_flight_api):
       agent = Agent(
           name="Flight Agent",
           tools=[search_flights]
       )

       result = await Runner.run(agent, "Find flights from SFO to NYC next week")
       assert "123" in result.final_output
       mock_flight_api.search.assert_called_once()
   ```

2. **Performance Optimization**

   - Use async operations for external API calls
   - Implement caching for frequently accessed data
   - Consider batch operations for database interactions
   - Profile and optimize tool implementations

3. **Deployment Considerations**
   - Set appropriate timeouts for production
   - Configure error handling and retries
   - Implement monitoring and alerting
   - Set up production-appropriate tracing
   - Consider scaling for concurrent users

## End-to-End Workflow

1. **Initialize Systems:** Knowledge graph and Supabase connection
2. **Initial Request Processing:** Parse travel request and query knowledge graph
3. **Information Gathering:** Ask follow-up questions
4. **Multi-Source Search:** Execute parallel searches and store results
5. **Optimization:** Apply sequential thinking for complex decisions
6. **Initial Recommendation:** Present optimized travel plan
7. **Exploration Phase:** Offer numbered exploration options
8. **Finalization:** Compile final itinerary with all details

## Security Guidelines

### Credential and API Key Management

1. **NEVER store sensitive information in any file that would be committed to the repository**

   - API keys, passwords, tokens, and other credentials must ALWAYS be stored in the `.env` file
   - The `.env` file should NEVER be committed to version control (already in `.gitignore`)
   - Always use `.env.example` with placeholder values (like `your-api-key-here`) to show required variables

2. **When updating documentation or example files:**

   - NEVER include actual API keys, project IDs or other sensitive values
   - Always use placeholder values like `your-project-id` or `your-anon-key`
   - Remove any accidentally committed sensitive information immediately

3. **Database Connection Security:**
   - Database URLs, connection strings, and authentication details must only be in `.env`
   - When documenting database connections, use only placeholder values
   - Do not include actual Supabase project IDs or API keys in README files or documentation
