# Reference Documentation

This directory contains reference documentation that provides standardized implementation examples, code patterns, and specs for the TripSage project.

## Purpose

The reference documents serve as the canonical source of truth for core technical details that apply across multiple parts of the system:

- Data schemas
- MCP implementation standards
- Agent SDK integration patterns
- Knowledge graph patterns
- Pydantic usage examples

## Contents

- `mcp_implementation.md` - Standard patterns for implementing MCP servers
- `memory_integration.md` - Knowledge graph integration patterns
- `openai_agents_sdk.md` - OpenAI Agents SDK integration examples
- `pydantic_examples.md` - Pydantic v2 usage examples
- `schema_details.md` - Database schema definitions

## Using Reference Documentation

When implementing new features, refer to these documents for standardized approaches and patterns. The reference documentation establishes consistent conventions and best practices across the codebase.

## Relationship to Implementation Docs

While implementation documents (`/docs/implementation/`) focus on specific features and components of the system, reference documents focus on technical standards and reusable patterns. Implementation docs may reference these documents when following established patterns.
