# Memory MCP Server Integration

This document outlines the implementation details for the Memory MCP Server, which provides knowledge graph capabilities for the TripSage travel planning system.

## Overview

The Memory MCP Server manages a travel-specific knowledge graph that stores entities (destinations, accommodations, etc.) and their relationships. This persistent knowledge graph enables TripSage to maintain context across user sessions and leverage patterns discovered in previous travel planning activities.

## Technology Selection

After evaluating multiple graph database options, we selected **Neo4j** with the **Drivine** TypeScript/Node.js client for the following reasons:

- **Strong TypeScript Support**: Drivine provides first-class TypeScript support with proper typing for queries and results
- **Mature Ecosystem**: Neo4j is a mature graph database with extensive documentation and community support
- **Performance**: Neo4j is optimized for graph traversal operations, which will be common in travel planning
- **Scalability**: Neo4j supports clustering for horizontal scaling as the knowledge base grows
- **Cypher Query Language**: Neo4j's Cypher provides a declarative, SQL-like syntax for graph queries

## Data Model

The knowledge graph is built around a comprehensive travel domain model with the following primary entities and relationships:

### Core Entities

- **Destination**: Cities, countries, or specific locations travelers can visit
- **PointOfInterest**: Attractions, landmarks, or specific sites within destinations
- **Accommodation**: Hotels, vacation rentals, hostels, etc.
- **Transportation**: Flights, trains, buses, rental cars, etc.
- **Activity**: Tours, experiences, or events available at destinations
- **Traveler**: User profiles with preferences and travel history
- **Trip**: A collection of travel components planned together
- **Review**: Feedback on any travel component

### Key Relationships

- **LOCATED_IN**: Geographic containment (e.g., PointOfInterest LOCATED_IN Destination)
- **NEAR**: Proximity relationship between entities
- **TRAVELED_TO**: Connection between Traveler and Destination
- **STAYED_AT**: Connection between Traveler and Accommodation
- **VISITED**: Connection between Traveler and PointOfInterest
- **INCLUDES**: Composition relationship (e.g., Trip INCLUDES Accommodation)
- **SIMILAR_TO**: Similarity relationship between entities of the same type
- **REVIEWED**: Connection between Traveler and any reviewable entity

### Entity Structure

Each entity in the knowledge graph includes:

- Unique identifier
- Type information
- Name
- Set of observations (additional attributes as free-form text)

## MCP Tools

The Memory MCP Server exposes the following tools:

### Entity Operations

- **create_entities**: Add new entities to the knowledge graph
- **delete_entities**: Remove entities and their associated relationships
- **search_nodes**: Find entities based on name, type, or observation content
- **open_nodes**: Retrieve detailed information about specific entities by name

### Relationship Operations

- **create_relations**: Create new relationships between entities
- **delete_relations**: Remove relationships between entities

### Observation Operations

- **add_observations**: Add new observations to existing entities
- **delete_observations**: Remove specific observations from entities

### Graph Operations

- **read_graph**: Retrieve the entire knowledge graph (with limits for large graphs)

## Implementation Details

### Server Architecture

The Memory MCP Server follows a clean architecture with separation of concerns:

1. **Models**: Define the data structures for entities and relationships
2. **Services**: Implement business logic and database operations
3. **Handlers**: Expose functionality as MCP tools
4. **Configuration**: Manage environment variables and connections

### Core Components

#### Entity Model

```typescript
// entity.model.ts
export interface Entity {
  id?: string;
  name: string;
  entityType: string;
  observations: string[];
}

export interface EntityCreateInput {
  name: string;
  entityType: string;
  observations: string[];
}

export interface EntitySearchParams {
  query: string;
}
```

#### Relation Model

```typescript
// relation.model.ts
export interface Relation {
  id?: string;
  from: string;
  to: string;
  relationType: string;
}

export interface RelationCreateInput {
  from: string;
  to: string;
  relationType: string;
}

export interface RelationDeleteInput {
  from: string;
  to: string;
  relationType: string;
}
```

#### Database Service

```typescript
// database.service.ts
import { Driver, Session } from "neo4j-driver";
import neo4j from "neo4j-driver";
import { injectable } from "inversify";
import { Logger } from "./logger";
import { ConfigService } from "./config.service";

@injectable()
export class DatabaseService {
  private driver: Driver;
  private logger = new Logger("DatabaseService");

  constructor(private configService: ConfigService) {
    const uri = this.configService.get("NEO4J_URI");
    const user = this.configService.get("NEO4J_USER");
    const password = this.configService.get("NEO4J_PASSWORD");

    this.driver = neo4j.driver(uri, neo4j.auth.basic(user, password));

    // Verify connection
    this.verifyConnectivity().catch((error) => {
      this.logger.error("Failed to connect to Neo4j", error);
      process.exit(1);
    });
  }

  async verifyConnectivity(): Promise<void> {
    await this.driver.verifyConnectivity();
    this.logger.info("Connected to Neo4j successfully");
  }

  getSession(): Session {
    return this.driver.session();
  }

  async close(): Promise<void> {
    await this.driver.close();
    this.logger.info("Neo4j connection closed");
  }
}
```

#### Entity Service

```typescript
// entity.service.ts
import { injectable } from "inversify";
import { DatabaseService } from "./database.service";
import {
  Entity,
  EntityCreateInput,
  EntitySearchParams,
} from "../models/entity.model";
import { Logger } from "./logger";

@injectable()
export class EntityService {
  private logger = new Logger("EntityService");

  constructor(private dbService: DatabaseService) {}

  async createEntities(entities: EntityCreateInput[]): Promise<Entity[]> {
    const session = this.dbService.getSession();
    const createdEntities: Entity[] = [];

    try {
      for (const entity of entities) {
        const result = await session.run(
          `CREATE (e:Entity {id: randomUUID(), name: $name, entityType: $entityType, observations: $observations})
           RETURN e`,
          {
            name: entity.name,
            entityType: entity.entityType,
            observations: entity.observations,
          }
        );

        if (result.records.length > 0) {
          const record = result.records[0].get("e").properties;
          createdEntities.push({
            id: record.id,
            name: record.name,
            entityType: record.entityType,
            observations: record.observations,
          });
        }
      }

      return createdEntities;
    } catch (error) {
      this.logger.error("Error creating entities", error);
      throw error;
    } finally {
      await session.close();
    }
  }

  async searchNodes(params: EntitySearchParams): Promise<Entity[]> {
    const session = this.dbService.getSession();

    try {
      const result = await session.run(
        `MATCH (e:Entity)
         WHERE e.name CONTAINS $query OR e.entityType CONTAINS $query OR 
               ANY(observation IN e.observations WHERE observation CONTAINS $query)
         RETURN e
         LIMIT 100`,
        { query: params.query }
      );

      return result.records.map((record) => {
        const props = record.get("e").properties;
        return {
          id: props.id,
          name: props.name,
          entityType: props.entityType,
          observations: props.observations,
        };
      });
    } catch (error) {
      this.logger.error("Error searching nodes", error);
      throw error;
    } finally {
      await session.close();
    }
  }

  // Additional methods would be implemented for other entity operations
}
```

#### Relation Service

```typescript
// relation.service.ts
import { injectable } from "inversify";
import { DatabaseService } from "./database.service";
import {
  Relation,
  RelationCreateInput,
  RelationDeleteInput,
} from "../models/relation.model";
import { Logger } from "./logger";

@injectable()
export class RelationService {
  private logger = new Logger("RelationService");

  constructor(private dbService: DatabaseService) {}

  async createRelations(relations: RelationCreateInput[]): Promise<Relation[]> {
    const session = this.dbService.getSession();
    const createdRelations: Relation[] = [];

    try {
      for (const relation of relations) {
        const result = await session.run(
          `MATCH (from:Entity {name: $fromName}), (to:Entity {name: $toName})
           CREATE (from)-[r:${relation.relationType} {id: randomUUID()}]->(to)
           RETURN from, r, to`,
          {
            fromName: relation.from,
            toName: relation.to,
          }
        );

        if (result.records.length > 0) {
          const record = result.records[0];
          createdRelations.push({
            id: record.get("r").properties.id,
            from: record.get("from").properties.name,
            to: record.get("to").properties.name,
            relationType: relation.relationType,
          });
        }
      }

      return createdRelations;
    } catch (error) {
      this.logger.error("Error creating relations", error);
      throw error;
    } finally {
      await session.close();
    }
  }

  // Additional methods would be implemented for other relation operations
}
```

#### Entity Handler

```typescript
// entity.handler.ts
import { injectable } from "inversify";
import { FastMCP, Tool } from "fastmcp";
import { EntityService } from "../services/entity.service";
import { EntityCreateInput, EntitySearchParams } from "../models/entity.model";
import { Logger } from "../services/logger";

@injectable()
export class EntityHandler {
  private logger = new Logger("EntityHandler");

  constructor(private entityService: EntityService, private mcp: FastMCP) {
    this.registerTools();
  }

  private registerTools(): void {
    this.mcp.registerTool({
      name: "create_entities",
      description: "Create multiple new entities in the knowledge graph",
      handler: this.createEntitiesHandler.bind(this),
      schema: {
        type: "object",
        properties: {
          entities: {
            type: "array",
            items: {
              type: "object",
              properties: {
                name: { type: "string" },
                entityType: { type: "string" },
                observations: {
                  type: "array",
                  items: { type: "string" },
                },
              },
              required: ["name", "entityType", "observations"],
            },
          },
        },
        required: ["entities"],
      },
    });

    this.mcp.registerTool({
      name: "search_nodes",
      description: "Search for nodes in the knowledge graph based on a query",
      handler: this.searchNodesHandler.bind(this),
      schema: {
        type: "object",
        properties: {
          query: { type: "string" },
        },
        required: ["query"],
      },
    });

    // Additional tool registrations would go here
  }

  async createEntitiesHandler(tool: Tool): Promise<any> {
    try {
      const input = tool.input as { entities: EntityCreateInput[] };
      const result = await this.entityService.createEntities(input.entities);
      return {
        success: true,
        entities: result,
      };
    } catch (error) {
      this.logger.error("Error in create_entities handler", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  async searchNodesHandler(tool: Tool): Promise<any> {
    try {
      const input = tool.input as EntitySearchParams;
      const result = await this.entityService.searchNodes(input);
      return {
        success: true,
        nodes: result,
      };
    } catch (error) {
      this.logger.error("Error in search_nodes handler", error);
      return {
        success: false,
        error: error.message,
      };
    }
  }

  // Additional handlers would be implemented for other entity tools
}
```

#### Server Entry Point

```typescript
// index.ts
import "reflect-metadata";
import { FastMCP } from "fastmcp";
import { Container } from "inversify";
import { ConfigService } from "./services/config.service";
import { DatabaseService } from "./services/database.service";
import { EntityService } from "./services/entity.service";
import { RelationService } from "./services/relation.service";
import { EntityHandler } from "./handlers/entity.handler";
import { RelationHandler } from "./handlers/relation.handler";
import { Logger } from "./services/logger";

const logger = new Logger("App");

async function bootstrap() {
  try {
    const container = new Container();

    // Register services
    container.bind(ConfigService).toSelf().inSingletonScope();
    container.bind(DatabaseService).toSelf().inSingletonScope();
    container.bind(EntityService).toSelf().inSingletonScope();
    container.bind(RelationService).toSelf().inSingletonScope();

    // Create MCP instance
    const mcp = new FastMCP({
      name: "memory",
      version: "1.0.0",
      description: "Memory MCP Server for TripSage knowledge graph",
    });

    container.bind(FastMCP).toConstantValue(mcp);

    // Register handlers
    container.bind(EntityHandler).toSelf().inSingletonScope();
    container.bind(RelationHandler).toSelf().inSingletonScope();

    // Get handler instances to register tools
    container.get(EntityHandler);
    container.get(RelationHandler);

    // Get database service to ensure connection
    const dbService = container.get(DatabaseService);

    // Start the server
    const port = container.get(ConfigService).get("PORT") || 3000;
    await mcp.listen(port);
    logger.info(`Memory MCP Server listening on port ${port}`);

    // Handle graceful shutdown
    const shutdown = async () => {
      logger.info("Shutting down Memory MCP Server...");
      await mcp.close();
      await dbService.close();
      process.exit(0);
    };

    process.on("SIGINT", shutdown);
    process.on("SIGTERM", shutdown);
  } catch (error) {
    logger.error("Failed to start Memory MCP Server", error);
    process.exit(1);
  }
}

bootstrap();
```

## Integration with TripSage

The Memory MCP Server integrates with the TripSage system in the following ways:

### Agent Integration

The Travel Agent leverages the Memory MCP in these key workflows:

1. **Initial Context Loading**: At the start of a conversation, the agent retrieves relevant travel knowledge using `search_nodes` and `read_graph`
2. **Pattern Recognition**: The agent can identify similar destinations or accommodations based on graph relationships
3. **Preference Storage**: User preferences are stored as entities and observations for future reference
4. **Trip History**: Completed trips are stored in the graph to inform future recommendations
5. **Continuous Learning**: New observations are added to entities as the system learns more about destinations and accommodations

### Data Flow

1. **Input**: Travel data from other MCP servers (Flights, Accommodations, Weather, etc.)
2. **Processing**: Data is transformed into entities and relationships
3. **Storage**: Entities and relationships are stored in the Neo4j graph database
4. **Retrieval**: The agent queries the graph database to inform travel planning decisions
5. **Update**: As users interact with the system, new observations and relationships are added

## Deployment and Configuration

### Environment Variables

| Variable       | Description                       | Default         |
| -------------- | --------------------------------- | --------------- |
| NEO4J_URI      | URI for Neo4j database            | None (Required) |
| NEO4J_USER     | Neo4j database username           | None (Required) |
| NEO4J_PASSWORD | Neo4j database password           | None (Required) |
| PORT           | Port for the MCP server           | 3000            |
| LOG_LEVEL      | Logging level (info, debug, etc.) | info            |

### Deployment Options

1. **Docker Container**: The recommended deployment method with Neo4j in a separate container
2. **Neo4j Aura**: Cloud-hosted Neo4j option for simplified management
3. **Kubernetes**: For production environments with high availability requirements

### Initialization

The Memory MCP Server requires initial setup to create the database schema and constraints:

```typescript
// init.ts - Run during first deployment
async function initializeDatabase() {
  const session = dbService.getSession();

  try {
    // Create constraints
    await session.run(`
      CREATE CONSTRAINT IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE
    `);

    // Create indexes
    await session.run(`
      CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.name)
    `);

    await session.run(`
      CREATE INDEX IF NOT EXISTS FOR (e:Entity) ON (e.entityType)
    `);

    logger.info("Database initialized successfully");
  } catch (error) {
    logger.error("Failed to initialize database", error);
    throw error;
  } finally {
    await session.close();
  }
}
```

## Best Practices

1. **Entity Naming**: Use consistent naming conventions for entities
2. **Relationship Types**: Use descriptive, verb-based relationship types (e.g., LOCATED_IN, VISITED)
3. **Query Optimization**: Limit depth of traversal queries to avoid performance issues
4. **Batch Operations**: Use batch operations for multiple entities or relationships
5. **Error Handling**: Implement robust error handling for all database operations
6. **Connection Management**: Properly manage database sessions and connections
7. **Validation**: Validate input data before creating entities or relationships

## Limitations and Future Enhancements

### Current Limitations

- Limited support for complex filtering in search operations
- No built-in visualization for knowledge graph exploration
- No automatic entity linking or relationship inference

### Planned Enhancements

1. **Semantic Search**: Implement vector embeddings for semantic similarity search
2. **Automatic Entity Linking**: Use NLP to automatically link related entities
3. **Relationship Inference**: Infer new relationships based on existing patterns
4. **Graph Analytics**: Add graph algorithms for recommendations and insights
5. **Visualization API**: Provide endpoints for graph visualization
6. **Bulk Import/Export**: Add tools for bulk data operations
7. **Versioning**: Implement versioning for entities and relationships

## Conclusion

The Memory MCP Server provides TripSage with a powerful knowledge graph backend that enables persistent storage of travel entities and their relationships. By maintaining this knowledge across user sessions, TripSage can provide increasingly personalized and informed travel recommendations based on accumulated knowledge and patterns.
