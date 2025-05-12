# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Table of Contents

- [Project Overview](#project-overview)
- [Technical Architecture](#technical-architecture)
- [Tool Integration Strategy](#tool-integration-strategy)
- [Git & GitHub Workflow](#git--github-workflow)
- [Coding & Style Guidelines](#coding--style-guidelines)
- [Agent Development Guidelines](#agent-development-guidelines)
- [Security Guidelines](#security-guidelines)
- [Reference Documents](#reference-documents)

## Project Overview

TripSage is an AI-powered travel planning system that seamlessly integrates flight, accommodation, and location data from multiple sources while storing search results in a dual-storage architecture (Supabase + knowledge graph memory). The system optimizes travel plans against budget constraints by comparing options across services, tracking price changes, and building a persistent knowledge base of travel relationships and patterns across sessions.

## Technical Architecture

### Dual Storage Architecture

- **Supabase Database:** Primary data store for structured travel information
  - Project Name: tripsage_planner
  - Key tables: trips, flights, accommodations, transportation
  - Use snake_case for all tables and columns
  - Include created_at and updated_at timestamps on all tables

See @docs/reference/schema_details.md for complete schema details

### Knowledge Graph Strategy

- **Travel Domain Knowledge Graph:** Stores travel-specific information
- **Project Meta-Knowledge Graph:** Stores information about the TripSage system itself

See @docs/reference/memory_integration.md for knowledge graph usage details

## Tool Integration Strategy

### MCP Servers & Tools Priority

1. Travel-specific MCP servers (flights-mcp, airbnb-mcp, google-maps-mcp)
2. Web search and research tools (linkup-mcp, firecrawl-mcp)
3. Database tools (supabase-mcp, memory-mcp)
4. Browser automation (playwright-mcp) - only when specialized tools insufficient
5. Time management tools (time-mcp) - for timezone and scheduling assistance
6. Reasoning tools (sequentialthinking-mcp) - for complex planning optimization

### MCP Server Implementation Guidelines

- Use FastMCP 2.0 for all MCP server implementations
- Implement proper validation for all inputs and outputs
- Use Pydantic models for complex data structures
- Apply validation constraints with Field and Annotated
- Leverage Context object for logging and progress reporting

See @docs/reference/mcp_implementation.md for detailed implementation examples

### Web Search Tools Usage

- Use Linkup Search Tool (search-web) as the default search tool

  - Use "standard" depth for straightforward queries
  - Use "deep" depth for complex queries
  - Handle one specific information need per search query

- Reserve Firecrawl Tools for specialized needs
  - Use firecrawl_scrape for detailed extraction from specific webpages
  - Use firecrawl_crawl for systematic exploration of websites

### Memory Knowledge Graph Usage

- Start each session with knowledge retrieval
- End each session with knowledge update
- Use appropriate memory operations:
  - read_graph to initialize context
  - search_nodes to find relevant trip patterns
  - create_entities for new travel concepts
  - create_relations for semantic relationships

### Playwright Usage Rules

- Only use Playwright when dedicated travel tools are insufficient
- When using Playwright, follow this sequence:
  1. Navigate to travel site
  2. Input search parameters
  3. Extract results
  4. Parse and store in dual storage architecture

## Git & GitHub Workflow

### Branch Strategy

- `main` - Production branch, protected
- `dev` - Development branch, protected
- Feature branches - Create from `dev`, name as `feature/descriptive-name`
- Fix branches - Create from `dev`, name as `fix/issue-description`

### Conventional Commits

Always use conventional commit format:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation only changes
- `style`: Changes that do not affect meaning
- `refactor`: Code change (not a fix or feature)
- `perf`: Performance improvement
- `test`: Adding or fixing tests
- `build`: Build system changes
- `ci`: CI configuration changes

## Coding & Style Guidelines

### Python Standards

- Follow PEP 8 and PEP 257 guidelines
- Use ruff for formatting and linting
- Include full type hints throughout all code
- Include docstrings for all functions, classes, and modules

### Logging Practices

- Use lazy logging to avoid string formatting overhead:

  ```python
  # CORRECT
  logger.debug("Message with %s and %d", string_var, int_var)

  # INCORRECT
  logger.debug(f"Message with {string_var} and {int_var}")
  ```

### Code Structure

- Keep files to a maximum of 300 lines
- Limit functions to 50 lines or less
- Use meaningful variable and function names

### Package Management

- Use `uv` for Python virtual environment management and package installation

### Design Principles

- **KISS** (Keep It Simple, Stupid) - Simplicity should be a key goal
- **DRY** (Don't Repeat Yourself) - Avoid code duplication
- **YAGNI** (You Aren't Gonna Need It) - Don't add functionality until necessary
- **SOLID** - Follow all SOLID principles
- Do not over-engineer solutions

See @docs/reference/pydantic_examples.md for Pydantic v2 usage examples

## Agent Development Guidelines

### Pattern Selection Framework

Choose the simplest effective pattern for each task:

1. **Single Augmented LLM Call** (First Choice)

   - For straightforward tasks with clear inputs/outputs
   - When the task doesn't require multiple steps

2. **Workflow Patterns** (Second Choice)

   - For predictable, decomposable tasks with known steps
   - When consistency and reliability are critical

3. **Autonomous Agent** (Last Resort)
   - For complex, unpredictable tasks requiring dynamic planning
   - When flexibility and model-driven decision-making are essential

### Core Agent Design Principles

1. **Simplicity First**

   - Start simple, add complexity only when necessary
   - Prefer fixed workflows for predictable tasks

2. **Transparency Always**

   - Make agent reasoning visible and explainable
   - Document all tool capabilities and limitations

3. **Careful Tool Design**

   - Create clear, well-documented tool interfaces
   - Design tools to be robust against invalid inputs

4. **Appropriate Guardrails**
   - Implement budget constraints as hard limits
   - Add safety checks for critical operations

See @docs/reference/openai_agents_sdk.md for OpenAI Agents SDK implementation details

## Security Guidelines

### Credential and API Key Management

1. **NEVER store sensitive information in repository files**

   - API keys, passwords, tokens must ALWAYS be in `.env`
   - The `.env` file should NEVER be committed
   - Use `.env.example` with placeholder values

2. **When updating documentation or examples:**
   - NEVER include actual API keys or project IDs
   - Always use placeholder values like `your-project-id`
   - Remove any accidentally committed sensitive information

## Reference Documents

- @docs/reference/schema_details.md - Detailed database schema information
- @docs/reference/pydantic_examples.md - Pydantic v2 usage examples
- @docs/reference/mcp_implementation.md - MCP server implementation examples
- @docs/reference/openai_agents_sdk.md - OpenAI Agents SDK implementation details
- @docs/reference/memory_integration.md - Memory knowledge graph usage
