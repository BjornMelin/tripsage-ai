"""Direct SDK service implementations.

This module contains direct SDK integrations for all services
that were previously accessed through MCP wrappers.

Services are organized into categories:
- api: API-specific services for HTTP operations
- core: Core business logic services
- infrastructure: Database, caching, and messaging services
- external: External API integration services
"""

# Re-export all services from subdirectories
from .api import *
from .core import *
from .infrastructure import *
from .external import *

# For backwards compatibility, also export specific services
from .infrastructure import DragonflyService as redis_service  # DragonflyDB replaces Redis
from .infrastructure import SupabaseService as supabase_service
from .infrastructure import DatabaseService as database_service
from .infrastructure import DragonflyService as cache_service
from .external import WebCrawlService as crawl4ai_service
from .external import PlaywrightService as playwright_service
from .external import WeatherService as weather_service
from .core import TimeService as time_service
from .external import FlightsService as flights_service
from .external import GoogleMapsService as maps_service
from .external import CalendarService as calendar_service
