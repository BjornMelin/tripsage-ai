# TripSage AI Travel Planning System Documentation

Welcome to the comprehensive documentation for the TripSage AI Travel Planning System. This documentation provides all the necessary information for understanding, developing, deploying, and maintaining the TripSage platform.

TripSage is an advanced AI-powered system designed to assist users in planning their travels seamlessly. It integrates various data sources, leverages sophisticated AI agents, and employs a robust architecture to deliver personalized and efficient travel itineraries.

## Navigating This Documentation

This documentation is organized into several key sections to help you find the information you need:

1. **[Project Overview and Planning](./01_PROJECT_OVERVIEW_AND_PLANNING/README.md)**:

   - High-level implementation plans, current project status, to-do lists, and reports on major refactoring or cleanup efforts.

2. **[System Architecture and Design](./02_SYSTEM_ARCHITECTURE_AND_DESIGN/README.md)**:

   - Detailed insights into the overall system architecture, agent design principles, optimization strategies, and deployment approaches.

3. **[Database and Storage](./03_DATABASE_AND_STORAGE/README.md)**:

   - Information on TripSage's unified storage architecture, including the Supabase PostgreSQL setup with pgvector extensions, Mem0 memory system integration, and migration details from legacy architectures.

4. **[MCP Servers](./04_MCP_SERVERS/README.md)**:

   - Documentation for all Model Context Protocol (MCP) servers, including general implementation patterns and specific guides for each server (Flights, Weather, WebCrawl, etc.).

5. **[Search and Caching](./05_SEARCH_AND_CACHING/README.md)**:

   - Strategies and implementation details for TripSage's hybrid search system and multi-level caching mechanisms.

6. **[Frontend](./06_FRONTEND/README.md)**:

   - Specifications, architecture, and technology stack for the TripSage user interface.

7. **[Installation and Setup](./07_INSTALLATION_AND_SETUP/README.md)**:

   - Step-by-step guides for setting up the development environment and installing TripSage components.

8. **[Reference](./08_REFERENCE/README.md)**:
   - Canonical examples, data schemas, and usage guides for core technologies like Pydantic, database schemas, and centralized settings.

9. **[Archived Documentation](./archived/README.md)**:
   - Historical documentation including completed research phases, comprehensive code reviews, and deprecated architectural approaches. This preserves development history while maintaining focus on current implementation guidance.

## Getting Started

If you are new to the project or setting up your development environment, please begin with the **[Installation Guide](./07_INSTALLATION_AND_SETUP/INSTALLATION_GUIDE.md)**.

For specific Node.js installation requirements and compatibility, refer to the **[Node.js Compatibility Guide](./07_INSTALLATION_AND_SETUP/node_js/COMPATIBILITY_GUIDE.md)**.

To understand the current development roadmap and status, refer to the **[Implementation Plan and Status](./01_PROJECT_OVERVIEW_AND_PLANNING/IMPLEMENTATION_PLAN_AND_STATUS.md)**.

For details on deployment strategies and CI/CD pipeline implementation, see the **[Deployment Strategy](./02_SYSTEM_ARCHITECTURE_AND_DESIGN/DEPLOYMENT_STRATEGY.md)**.

## Contributing

Please refer to the project's main `CONTRIBUTING.md` (if available in the root of the repository) for guidelines on contributing to the TripSage project. Ensure that any code contributions are accompanied by relevant documentation updates.

## Documentation Standards

All documentation within this `docs` directory aims to be:

- **Clear and Concise**: Easy to understand and to the point.
- **Accurate**: Reflecting the current state of the project.
- **Comprehensive**: Covering all necessary aspects of the system.
- **Well-Organized**: Logically structured for easy navigation.
- **Up-to-Date**: Regularly maintained as the project evolves.

We encourage you to explore the relevant sections based on your area of interest or development task.
