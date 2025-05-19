# Reference Documentation

This section of the TripSage documentation serves as a repository for canonical examples, technical standards, data schema definitions, and reusable patterns that apply across multiple parts of the system. It is intended to be a source of truth for core implementation details.

## Purpose

The reference documents aim to:

* Provide standardized implementation examples for key technologies and libraries used in TripSage (e.g., Pydantic).
* Define and detail critical data structures, such as database schemas.
* Explain the workings of core systems like the centralized configuration.
* Offer guidance on integrating with fundamental external APIs that underpin various MCP services.
* Ensure consistency and adherence to best practices across the codebase.

## Contents

* **[Pydantic Usage](./Pydantic_Usage.md)**:
  * Illustrates best practices and common patterns for using Pydantic v2 for data validation, schema definition, and settings management within the TripSage project.

* **[Database Schema Details](./Database_Schema_Details.md)**:
  * Provides detailed definitions for all tables in the TripSage relational database (PostgreSQL via Supabase/Neon), including column types, constraints, and descriptions.

* **[Centralized Settings System](./Centralized_Settings.md)**:
  * Explains the Pydantic-based centralized configuration system, how to access settings, and how to extend it.

* **[Key API Integrations](./Key_API_Integrations.md)**:
  * Details the integration strategy for fundamental external APIs that are wrapped by or support TripSage's MCP servers (e.g., Duffel API for flights, Google Maps Platform API). Includes authentication flows, key endpoints, and data exchange patterns. This document also incorporates comparisons of different API options considered.

## Using This Reference Documentation

Developers should consult these documents when:

* Implementing new features that involve core data models or technologies.
* Seeking to understand the standard way of performing certain tasks (e.g., data validation, configuration access).
* Needing detailed information about database structures or external API contracts.

While implementation-specific guides are found in other sections (like `04_MCP_SERVERS` or `03_DATABASE_AND_STORAGE`), this reference section provides the foundational technical details and patterns that those implementations rely upon.
