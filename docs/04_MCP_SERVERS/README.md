# TripSage Service Integration Guide (MCP → SDK Migration)

## 🚨 MAJOR ARCHITECTURE CHANGE 🚨

TripSage has **completed migration from MCP servers to direct SDK integration** for dramatically improved performance and simplified architecture. This section documents the final remaining MCP integration and the new unified SDK approach.

**NEW ARCHITECTURE**: 7 direct SDK integrations + 1 MCP server (Airbnb only) replacing 12 original MCP servers.

**PERFORMANCE GAINS**: 50-70% latency reduction, 6-10x crawling improvement, ~3000 lines code reduction.

## Migration Status (January 2025)

**✅ MIGRATION COMPLETED**: TripSage has successfully migrated to direct SDK integration for all services except Airbnb accommodations.

**Services migrated to direct SDKs:**

- ✅ **Flights**: Direct Duffel SDK integration
- ✅ **Weather**: Direct weather API integration  
- ✅ **Time**: Direct time API integration
- ✅ **Memory**: Direct Mem0 SDK with Supabase PostgreSQL backend
- ✅ **WebCrawl**: Direct Crawl4AI integration (Firecrawl deprecated)
- ✅ **Calendar**: Direct Google Calendar SDK integration
- ✅ **Google Maps**: Direct Google Maps SDK integration
- ✅ **Browser Automation**: Direct Playwright SDK integration
- ✅ **Database**: Direct Supabase SDK integration
- ✅ **Cache/Redis**: Direct Redis client integration

**Remaining MCP integration:**

- 🏠 **Accommodations**: Airbnb via OpenBnB MCP server (external, well-maintained)

## Overview of Current Architecture

TripSage now employs a **minimal MCP strategy** with only one external MCP integration:

1. **Single External MCP**: The **OpenBnB Airbnb MCP Server** (`@openbnb/mcp-server-airbnb`) provides access to Airbnb listing data. This remains as an MCP because:
   - It's a well-maintained external MCP server
   - Airbnb doesn't provide a public API
   - The OpenBnB MCP handles the complexities of Airbnb data access
   - No direct SDK alternative exists

2. **Direct SDK Integrations**: All other services use direct SDK/API integration for:
   - Better performance (50-70% latency reduction)
   - Simplified debugging and development
   - Reduced abstraction overhead
   - More reliable error handling

All interactions with the remaining MCP server are managed through a **simplified MCP Abstraction Layer** that only supports Airbnb accommodations.

## Contents

This section contains the implementation guide for the remaining MCP integration:

- **[Accommodations MCP](./Accommodations_MCP.md)**:
  - The only remaining MCP integration in TripSage
  - Handles Airbnb listing search and details via OpenBnB MCP server
  - Includes integration with Booking.com via direct Apify API (not MCP)
  - Provides unified accommodation search across multiple providers

## Quick Start

### Using the Simplified MCP System

Start the Airbnb MCP server:

```bash
# Start the OpenBnB Airbnb MCP server
npx -y @openbnb/mcp-server-airbnb
```

### Configuration

The simplified MCP configuration only includes Airbnb:

```python
# tripsage/config/mcp_settings.py
from tripsage.config.mcp_settings import mcp_settings

# Access the only remaining MCP configuration
airbnb_config = mcp_settings.airbnb

# Check if enabled
if mcp_settings.airbnb.enabled:
    # Use Airbnb MCP
    pass
```

## Development and Integration

When developing new features that require external service interaction:

1. **First choice**: Use direct SDK/API integration for better performance
2. **Only use MCP**: When no direct API exists or when leveraging a well-maintained external MCP server (like OpenBnB for Airbnb)

### Implementation Details

The remaining MCP integration follows these patterns:

1. **Configuration**: Defined in `tripsage/config/mcp_settings.py` (simplified to only Airbnb)
2. **Wrapper**: Located in `tripsage/mcp_abstraction/wrappers/airbnb_wrapper.py`
3. **Tools**: Exposed in `tripsage/tools/accommodations_tools.py`
4. **Tests**: Coverage in `tests/unit/agents/test_accommodations.py`

### Direct SDK Integration Examples

For reference on the new direct SDK approach, see:

- **Flights**: `tripsage/services/duffel_http_client.py`
- **Maps**: `tripsage/services/google_maps_service.py`
- **Database**: `tripsage/services/supabase_service.py`
- **Cache**: `tripsage/services/redis_service.py`
- **WebCrawl**: `tripsage/services/webcrawl_service.py`

## Migration Benefits Achieved

The migration from 12 MCP servers to 1 MCP + 7 direct SDKs has delivered:

- **Performance**: 50-70% improvement in P95 latency
- **Code Simplicity**: ~3,000 lines of wrapper code removed
- **Development Speed**: Faster debugging with direct service calls
- **Reliability**: Better error handling and monitoring
- **Cost Savings**: $1,500-2,000/month in infrastructure costs
- **Maintenance**: Simplified architecture with fewer moving parts

## Future Considerations

- **Airbnb MCP**: Will remain as long as OpenBnB MCP server is well-maintained and no direct Airbnb API becomes available
- **New Integrations**: All future service integrations should use direct SDK/API approach unless compelling reasons exist for MCP
- **Performance Monitoring**: Continue monitoring the single remaining MCP integration for any performance issues
