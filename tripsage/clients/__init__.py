"""Client implementations for external services and MCPs.

After the MCP to SDK migration, this module only contains:
- AccommodationMCPClient: For Airbnb accommodations (only service remaining on MCP)
- MCPClientFactory: Factory for creating Airbnb MCP clients

All other services have been migrated to direct SDK integration:
- Redis → Direct redis-py SDK (tripsage.services.redis_service)
- Supabase → Direct supabase-py SDK (tripsage.services.supabase_service)
- Weather → Weather API direct integration (Week 4)
- Maps → Google Maps Python client (Week 4)
- Flights → Duffel API SDK (Week 3-4)
- Memory → Neo4j driver direct integration (Week 2)
- Webcrawl → Crawl4AI direct SDK integration (completed)
"""

from tripsage.clients.accommodations import AccommodationMCPClient
from tripsage.clients.factory import MCPClientFactory

__all__ = ["AccommodationMCPClient", "MCPClientFactory"]
