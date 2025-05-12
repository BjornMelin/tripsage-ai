# TripSage Redis Caching Implementation Guide

This document provides a detailed implementation guide for setting up and optimizing the Redis caching system for TripSage, with a specific focus on search result caching.

## 1. Overview

TripSage implements a multi-level caching strategy using Redis to optimize API interactions, reduce latency, and manage rate limits. This approach is critical for travel applications, which deal with:

- High-volume flight and accommodation search requests
- Varying data volatility (prices vs. static information)
- API rate limits and usage costs
- Cross-service data sharing requirements

## 2. Redis Setup and Configuration

### 2.1 Redis Installation and Configuration

#### Development Environment

```bash
# Install Redis using Docker
docker run --name tripsage-redis -p 6379:6379 -d redis:7.0-alpine

# Test connection
docker exec -it tripsage-redis redis-cli ping
```

#### Production Environment

For production, configure Redis with:

```conf
# /etc/redis/redis.conf

# Performance settings
maxmemory 4gb
maxmemory-policy volatile-ttl
appendonly yes
appendfsync everysec

# Connection settings
bind 0.0.0.0
protected-mode yes
requirepass your_strong_password

# Persistence settings
save 900 1
save 300 10
save 60 10000

# Advanced settings
activerehashing yes
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
```

Deploy Redis in production using a managed service or in a containerized environment:

```yaml
# docker-compose.yml (Redis service)
services:
  redis:
    image: redis:7.0-alpine
    command: redis-server /etc/redis/redis.conf
    volumes:
      - ./redis.conf:/etc/redis/redis.conf
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - tripsage-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 10s

volumes:
  redis-data:

networks:
  tripsage-network:
    driver: bridge
```

### 2.2 Redis Client Implementation

Install the Redis client library:

```bash
uv pip install redis
```

Implement the Redis client:

```python
# src/cache/redis_cache.py
import json
import logging
import os
from typing import Any, Dict, Optional, Union, List, TypeVar, Generic
from datetime import datetime, timedelta
import redis
from redis.exceptions import RedisError
from functools import wraps
import hashlib

# Type variable for generic caching
T = TypeVar('T')

logger = logging.getLogger(__name__)

class RedisCache:
    """Redis caching implementation for TripSage."""

    def __init__(self,
                url: Optional[str] = None,
                ttl: int = 3600,
                namespace: str = "tripsage"):
        """Initialize Redis connection.

        Args:
            url: Redis connection URL (defaults to env var REDIS_URL)
            ttl: Default TTL in seconds (defaults to 1 hour)
            namespace: Namespace prefix for all keys
        """
        self.url = url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self.default_ttl = ttl
        self.namespace = namespace
        self._client = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Redis."""
        try:
            self._client = redis.from_url(
                self.url,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
                socket_keepalive=True,
                retry_on_timeout=True,
                decode_responses=False
            )
            # Test connection
            self._client.ping()
            logger.info(f"Connected to Redis at {self.url}")
        except RedisError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def _format_key(self, key: str) -> str:
        """Format key with namespace.

        Args:
            key: Original key

        Returns:
            Formatted key with namespace
        """
        return f"{self.namespace}:{key}"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        formatted_key = self._format_key(key)

        try:
            value = self._client.get(formatted_key)
            if value is None:
                logger.debug(f"Cache miss for key: {key}")
                return None

            logger.debug(f"Cache hit for key: {key}")
            return json.loads(value)
        except RedisError as e:
            logger.error(f"Redis error in get(): {str(e)}")
            return None
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error deserializing cached value: {str(e)}")
            return None

    async def set(self,
                key: str,
                value: Any,
                ttl: Optional[int] = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (optional, defaults to instance default)

        Returns:
            True if successful, False otherwise
        """
        formatted_key = self._format_key(key)
        expiry = ttl if ttl is not None else self.default_ttl

        try:
            serialized = json.dumps(value)
            result = self._client.setex(
                formatted_key,
                expiry,
                serialized
            )
            logger.debug(f"Set cache key: {key} with TTL: {expiry}s")
            return result
        except RedisError as e:
            logger.error(f"Redis error in set(): {str(e)}")
            return False
        except (TypeError, OverflowError) as e:
            logger.error(f"Error serializing value for cache: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if successful, False otherwise
        """
        formatted_key = self._format_key(key)

        try:
            result = self._client.delete(formatted_key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)
        except RedisError as e:
            logger.error(f"Redis error in delete(): {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        formatted_key = self._format_key(key)

        try:
            return bool(self._client.exists(formatted_key))
        except RedisError as e:
            logger.error(f"Redis error in exists(): {str(e)}")
            return False

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get TTL for a key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, or None if key doesn't exist
        """
        formatted_key = self._format_key(key)

        try:
            ttl = self._client.ttl(formatted_key)
            return ttl if ttl > 0 else None
        except RedisError as e:
            logger.error(f"Redis error in get_ttl(): {str(e)}")
            return None

    async def clear_namespace(self) -> bool:
        """Clear all keys in the current namespace.

        Returns:
            True if successful, False otherwise
        """
        try:
            pattern = f"{self.namespace}:*"
            cursor = 0
            deleted_count = 0

            while True:
                cursor, keys = self._client.scan(cursor, pattern, 100)
                if keys:
                    deleted_count += self._client.delete(*keys)

                if cursor == 0:
                    break

            logger.info(f"Cleared {deleted_count} keys from namespace: {self.namespace}")
            return True
        except RedisError as e:
            logger.error(f"Redis error in clear_namespace(): {str(e)}")
            return False

    def cached(self, key_pattern: str, ttl: Optional[int] = None):
        """Decorator to cache function results.

        Args:
            key_pattern: Key pattern with placeholders (e.g. "user:{0}:profile")
            ttl: Cache TTL in seconds (overrides default)

        Returns:
            Decorated function
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                try:
                    # Format key with args and kwargs
                    arg_values = []
                    for arg in args[1:]:  # Skip self if present
                        if isinstance(arg, (str, int, float, bool)) or arg is None:
                            arg_values.append(str(arg))
                        else:
                            arg_values.append(hashlib.md5(str(arg).encode()).hexdigest())

                    kwarg_values = []
                    for k, v in sorted(kwargs.items()):
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            kwarg_values.append(f"{k}:{v}")
                        else:
                            kwarg_values.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()}")

                    formatted_args = ":".join(arg_values)
                    formatted_kwargs = ":".join(kwarg_values)

                    key_parts = [key_pattern]
                    if formatted_args:
                        key_parts.append(formatted_args)
                    if formatted_kwargs:
                        key_parts.append(formatted_kwargs)

                    cache_key = ":".join(key_parts)

                    # Check cache
                    cached_value = await self.get(cache_key)
                    if cached_value is not None:
                        return cached_value

                    # Call original function
                    result = await func(*args, **kwargs)

                    # Cache result
                    await self.set(cache_key, result, ttl)

                    return result
                except Exception as e:
                    logger.error(f"Error in cached decorator: {str(e)}")
                    # Call original function without caching
                    return await func(*args, **kwargs)

            return wrapper

        return decorator
```

### 2.3 TTL Configuration by Data Type

In your configuration module, set up TTL values based on data volatility:

```python
# src/utils/config.py
from typing import Dict, Any
import os

# Cache TTL configuration (in seconds)
CACHE_TTL: Dict[str, int] = {
    # Search results
    "FLIGHT_SEARCH": 10 * 60,  # 10 minutes
    "HOTEL_SEARCH": 30 * 60,   # 30 minutes
    "ACTIVITY_SEARCH": 60 * 60, # 1 hour

    # Lookups
    "AIRPORT": 24 * 60 * 60,   # 24 hours
    "AIRLINE": 24 * 60 * 60,   # 24 hours
    "CITY": 7 * 24 * 60 * 60,  # 7 days

    # Details
    "FLIGHT_DETAILS": 5 * 60,  # 5 minutes
    "HOTEL_DETAILS": 15 * 60,  # 15 minutes

    # User data
    "USER_PREFERENCES": 15 * 60, # 15 minutes

    # API Responses
    "WEATHER": 60 * 60,         # 1 hour
    "EXCHANGE_RATE": 60 * 60,   # 1 hour

    # System defaults
    "DEFAULT": 30 * 60          # 30 minutes
}

# Redis configuration
REDIS_CONFIG = {
    "URL": os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
    "DEFAULT_TTL": CACHE_TTL["DEFAULT"],
    "NAMESPACE": "tripsage"
}
```

## 3. Search Results Caching Implementation

### 3.1 Cache Key Generation

For effective caching, implement standardized cache key generation:

```python
# src/cache/key_generator.py
import hashlib
import json
from typing import Dict, Any, List, Union

def generate_flight_search_key(params: Dict[str, Any]) -> str:
    """Generate standardized cache key for flight search.

    Args:
        params: Flight search parameters

    Returns:
        Standardized cache key
    """
    # Extract essential parameters
    key_params = {
        "origin": params.get("origin", "").upper(),
        "destination": params.get("destination", "").upper(),
        "departure_date": params.get("departure_date", ""),
        "return_date": params.get("return_date", ""),
        "adults": params.get("adults", 1),
        "children": params.get("children", 0),
        "infants": params.get("infants", 0),
        "cabin_class": params.get("cabin_class", "economy").lower()
    }

    # Add optional parameters if present
    if "max_connections" in params:
        key_params["max_connections"] = params["max_connections"]

    if "airline_codes" in params and params["airline_codes"]:
        key_params["airline_codes"] = sorted(params["airline_codes"])

    # Create key parts
    route = f"{key_params['origin']}-{key_params['destination']}"
    dates = f"{key_params['departure_date']}"
    if key_params["return_date"]:
        dates += f"~{key_params['return_date']}"

    travelers = f"{key_params['adults']}a-{key_params['children']}c-{key_params['infants']}i"

    # Include other parameters as JSON hash to keep key length reasonable
    other_params = {}
    for k, v in key_params.items():
        if k not in ["origin", "destination", "departure_date", "return_date",
                     "adults", "children", "infants"]:
            other_params[k] = v

    other_params_str = ""
    if other_params:
        other_params_str = hashlib.md5(json.dumps(other_params, sort_keys=True).encode()).hexdigest()[:8]

    # Combine parts
    cache_key = f"flights:search:{route}:{dates}:{travelers}"
    if other_params_str:
        cache_key += f":{other_params_str}"

    return cache_key

def generate_hotel_search_key(params: Dict[str, Any]) -> str:
    """Generate standardized cache key for hotel search.

    Args:
        params: Hotel search parameters

    Returns:
        Standardized cache key
    """
    # Extract essential parameters
    key_params = {
        "location": params.get("location", "").lower(),
        "check_in": params.get("check_in_date", ""),
        "check_out": params.get("check_out_date", ""),
        "guests": params.get("adults", 1) + params.get("children", 0),
        "rooms": params.get("rooms", 1)
    }

    # Add optional parameters
    optional_params = {}
    for param in ["min_price", "max_price", "min_rating", "amenities", "property_type"]:
        if param in params and params[param] is not None:
            if param == "amenities" and params[param]:
                optional_params[param] = sorted(params[param])
            else:
                optional_params[param] = params[param]

    # Create key parts
    location = key_params["location"].replace(" ", "_")
    dates = f"{key_params['check_in']}~{key_params['check_out']}"
    guests = f"{key_params['guests']}g-{key_params['rooms']}r"

    # Include other parameters as JSON hash
    other_params_str = ""
    if optional_params:
        other_params_str = hashlib.md5(json.dumps(optional_params, sort_keys=True).encode()).hexdigest()[:8]

    # Combine parts
    cache_key = f"hotels:search:{location}:{dates}:{guests}"
    if other_params_str:
        cache_key += f":{other_params_str}"

    return cache_key
```

### 3.2 TTL Determination Logic

Implement dynamic TTL calculation based on search parameters and volatility:

```python
# src/cache/ttl_manager.py
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from src.utils.config import CACHE_TTL

def calculate_flight_search_ttl(params: Dict[str, Any], results: Dict[str, Any]) -> int:
    """Calculate appropriate TTL for flight search results.

    Args:
        params: Search parameters
        results: Search results

    Returns:
        TTL in seconds
    """
    base_ttl = CACHE_TTL["FLIGHT_SEARCH"]

    # Adjust TTL based on search date proximity
    if "departure_date" in params:
        try:
            departure_date = datetime.fromisoformat(params["departure_date"])
            days_until_departure = (departure_date - datetime.now()).days

            if days_until_departure < 3:
                # Flights within 3 days - reduce TTL by 50%
                return int(base_ttl * 0.5)
            elif days_until_departure < 7:
                # Flights within a week - reduce TTL by 25%
                return int(base_ttl * 0.75)
            elif days_until_departure > 90:
                # Flights more than 3 months away - increase TTL by 50%
                return int(base_ttl * 1.5)
        except (ValueError, TypeError):
            pass

    # Adjust TTL based on result count
    result_count = len(results.get("offers", []))
    if result_count < 5:
        # Few results - reduce TTL to refresh sooner
        return int(base_ttl * 0.75)
    elif result_count > 50:
        # Many results - can cache longer
        return int(base_ttl * 1.25)

    return base_ttl

def calculate_hotel_search_ttl(params: Dict[str, Any], results: Dict[str, Any]) -> int:
    """Calculate appropriate TTL for hotel search results.

    Args:
        params: Search parameters
        results: Search results

    Returns:
        TTL in seconds
    """
    base_ttl = CACHE_TTL["HOTEL_SEARCH"]

    # Adjust TTL based on check-in date proximity
    if "check_in_date" in params:
        try:
            check_in_date = datetime.fromisoformat(params["check_in_date"])
            days_until_check_in = (check_in_date - datetime.now()).days

            if days_until_check_in < 7:
                # Stays within a week - reduce TTL by 40%
                return int(base_ttl * 0.6)
            elif days_until_check_in < 14:
                # Stays within two weeks - reduce TTL by 20%
                return int(base_ttl * 0.8)
            elif days_until_check_in > 60:
                # Stays more than 2 months away - increase TTL by 30%
                return int(base_ttl * 1.3)
        except (ValueError, TypeError):
            pass

    # Adjust TTL based on result count and seasonality
    result_count = len(results.get("accommodations", []))

    # Check if this is peak travel season for the destination
    is_peak_season = _is_peak_season(params.get("location", ""))

    if is_peak_season:
        # High season - reduce TTL by 25%
        return int(base_ttl * 0.75)
    elif result_count < 10:
        # Few results - reduce TTL
        return int(base_ttl * 0.8)

    return base_ttl

def _is_peak_season(location: str) -> bool:
    """Determine if the current date is in peak season for a location.

    This is a simplified implementation. In practice, this would use a
    database of seasonal data for different destinations.

    Args:
        location: Location name

    Returns:
        True if current date is in peak season for the location
    """
    current_month = datetime.now().month

    # Simple seasonal mapping (would be replaced with actual data)
    peak_months = {
        "paris": [5, 6, 7, 8, 9],  # Summer
        "new york": [5, 6, 9, 10, 11, 12],  # Spring and Fall
        "tokyo": [3, 4, 10, 11],  # Cherry blossom and autumn
        "bali": [6, 7, 8, 9],  # Dry season
        "sydney": [12, 1, 2],  # Summer in Southern Hemisphere
    }

    # Default to general Northern Hemisphere summer if location not found
    location_key = location.lower()
    relevant_months = peak_months.get(location_key, [6, 7, 8])

    return current_month in relevant_months
```

### 3.3 Integration with MCP Clients

Implement caching in the Flight MCP Client:

```python
# src/mcp/flights/client.py
from typing import Dict, List, Any, Optional, Union
from datetime import date, datetime
from pydantic import BaseModel, Field, field_validator, ValidationInfo
from agents import function_tool
from src.mcp.base_mcp_client import BaseMCPClient
from src.utils.logging import get_module_logger
from src.cache.redis_cache import RedisCache
from src.cache.key_generator import generate_flight_search_key
from src.cache.ttl_manager import calculate_flight_search_ttl
from src.utils.config import REDIS_CONFIG, CACHE_TTL

logger = get_module_logger(__name__)
redis_cache = RedisCache(
    url=REDIS_CONFIG["URL"],
    ttl=REDIS_CONFIG["DEFAULT_TTL"],
    namespace=REDIS_CONFIG["NAMESPACE"]
)

class FlightsMCPClient(BaseMCPClient):
    """Client for the Flights MCP Server with integrated caching."""

    def __init__(self):
        """Initialize the Flights MCP client."""
        super().__init__(server_name="flights")
        logger.info("Initialized Flights MCP Client")

    @function_tool
    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: Union[str, date],
        return_date: Optional[Union[str, date]] = None,
        adults: int = 1,
        children: int = 0,
        infants: int = 0,
        cabin_class: str = "economy",
        max_connections: Optional[int] = None,
        airline_codes: Optional[List[str]] = None,
        currency: str = "USD",
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """Search for flights between origin and destination.

        Args:
            origin: Origin airport code (e.g., 'LAX')
            destination: Destination airport code (e.g., 'JFK')
            departure_date: Departure date in YYYY-MM-DD format
            return_date: Return date in YYYY-MM-DD format for round trips
            adults: Number of adult passengers
            children: Number of child passengers (2-11 years)
            infants: Number of infant passengers (<2 years)
            cabin_class: Preferred cabin class
            max_connections: Maximum number of connections per slice
            airline_codes: Limit results to specific airlines (IATA codes)
            currency: Currency for prices (ISO 4217 code)
            skip_cache: Whether to skip cache and force a fresh search

        Returns:
            Dictionary with search results
        """
        try:
            # Convert date objects to strings if needed
            if isinstance(departure_date, date):
                departure_date = departure_date.isoformat()

            if return_date and isinstance(return_date, date):
                return_date = return_date.isoformat()

            # Prepare search parameters
            params = {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "children": children,
                "infants": infants,
                "cabin_class": cabin_class,
                "currency": currency
            }

            # Add optional parameters if provided
            if max_connections is not None:
                params["max_connections"] = max_connections

            if airline_codes:
                params["airline_codes"] = airline_codes

            # Generate cache key
            cache_key = generate_flight_search_key(params)

            # Check cache first (unless skipping)
            if not skip_cache:
                cached_result = await redis_cache.get(cache_key)
                if cached_result:
                    logger.info(f"Retrieved flight search results from cache: {origin} to {destination}")
                    # Add cache metadata
                    ttl = await redis_cache.get_ttl(cache_key)
                    if ttl:
                        cached_result["_cache"] = {
                            "cached_at": datetime.now().isoformat(),
                            "expires_in": ttl,
                            "source": "redis"
                        }
                    return cached_result

            # Call MCP server for fresh results
            logger.info(f"Performing fresh flight search: {origin} to {destination}")
            server = await self.get_server()
            result = await server.invoke_tool(
                "search_flights",
                params
            )

            # Cache the results with appropriate TTL
            if result and "error" not in result:
                ttl = calculate_flight_search_ttl(params, result)
                await redis_cache.set(cache_key, result, ttl)
                logger.info(f"Cached flight search results for {ttl} seconds")

            return result
        except Exception as e:
            logger.error(f"Error searching flights: {str(e)}")
            return {
                "error": f"Failed to search flights: {str(e)}",
                "origin": origin,
                "destination": destination
            }
```

Similarly, implement caching for other MCP clients like accommodations.

### 3.4 Stale-While-Revalidate Pattern

For improved user experience, implement the stale-while-revalidate pattern:

```python
# src/cache/stale_handler.py
import asyncio
from typing import Dict, Any, Callable, Awaitable, Optional, Tuple
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class StaleWhileRevalidateHandler:
    """Handles stale-while-revalidate pattern for caching."""

    def __init__(self):
        """Initialize the handler."""
        self.background_tasks = {}

    async def get_or_refresh(self,
                           cache_key: str,
                           cache_get_func: Callable[[str], Awaitable[Optional[Any]]],
                           cache_set_func: Callable[[str, Any, int], Awaitable[bool]],
                           refresh_func: Callable[[], Awaitable[Any]],
                           ttl: int,
                           stale_ttl: int) -> Tuple[Any, bool]:
        """Get value from cache or refresh in background.

        Args:
            cache_key: Cache key
            cache_get_func: Function to get from cache
            cache_set_func: Function to set in cache
            refresh_func: Function to refresh the data
            ttl: Fresh TTL in seconds
            stale_ttl: Additional time data can be used while stale

        Returns:
            Tuple of (value, is_fresh)
        """
        # Get from cache
        cached_value = await cache_get_func(cache_key)

        # If not in cache, refresh synchronously
        if cached_value is None:
            logger.debug(f"Cache miss for key: {cache_key}, fetching fresh data")
            fresh_value = await refresh_func()
            if fresh_value is not None:
                await cache_set_func(cache_key, fresh_value, ttl + stale_ttl)
            return fresh_value, True

        # Check if refresh already in progress
        if cache_key in self.background_tasks:
            if not self.background_tasks[cache_key].done():
                logger.debug(f"Using cached data for {cache_key}, refresh already in progress")
                return cached_value, False
            # Clean up completed task
            del self.background_tasks[cache_key]

        # Start background refresh if TTL is expired but still within stale window
        remaining_ttl = await self._get_ttl(cache_key, cache_get_func)
        if remaining_ttl is not None and remaining_ttl <= stale_ttl:
            logger.debug(f"Using stale data for {cache_key}, refreshing in background")
            self.background_tasks[cache_key] = asyncio.create_task(
                self._background_refresh(cache_key, refresh_func, cache_set_func, ttl, stale_ttl)
            )
            return cached_value, False

        return cached_value, True

    async def _background_refresh(self,
                               cache_key: str,
                               refresh_func: Callable[[], Awaitable[Any]],
                               cache_set_func: Callable[[str, Any, int], Awaitable[bool]],
                               ttl: int,
                               stale_ttl: int) -> None:
        """Refresh data in background.

        Args:
            cache_key: Cache key
            refresh_func: Function to refresh the data
            cache_set_func: Function to set in cache
            ttl: Fresh TTL in seconds
            stale_ttl: Additional time data can be used while stale
        """
        try:
            logger.debug(f"Starting background refresh for {cache_key}")
            fresh_value = await refresh_func()
            if fresh_value is not None:
                await cache_set_func(cache_key, fresh_value, ttl + stale_ttl)
                logger.debug(f"Background refresh completed for {cache_key}")
        except Exception as e:
            logger.error(f"Error in background refresh for {cache_key}: {str(e)}")

    async def _get_ttl(self,
                    cache_key: str,
                    cache_get_func: Callable[[str], Awaitable[Optional[int]]]) -> Optional[int]:
        """Get TTL for a cache key.

        Args:
            cache_key: Cache key
            cache_get_func: Function to get TTL

        Returns:
            TTL in seconds or None
        """
        try:
            return await cache_get_func(cache_key)
        except Exception as e:
            logger.error(f"Error getting TTL for {cache_key}: {str(e)}")
            return None
```

## 4. Rate Limiting and API Management

### 4.1 Redis-Based Rate Limiter

Implement a rate limiter to manage API quota:

```python
# src/cache/rate_limiter.py
import time
from typing import Dict, Any, Optional, Tuple
from src.cache.redis_cache import RedisCache
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class RateLimiter:
    """Redis-based rate limiter for API calls."""

    def __init__(self, redis_cache: RedisCache):
        """Initialize rate limiter.

        Args:
            redis_cache: Redis cache instance
        """
        self.redis = redis_cache

    async def check_limit(self,
                        key: str,
                        limit: int,
                        window: int) -> Tuple[bool, int, int]:
        """Check if rate limit is exceeded.

        Args:
            key: Rate limit key (e.g., 'api:flights:search')
            limit: Maximum number of requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (allowed, remaining, retry_after)
        """
        try:
            # Current timestamp
            now = int(time.time())

            # Window start timestamp
            window_start = now - window

            # Redis key for this rate limit
            redis_key = f"ratelimit:{key}"

            # Execute rate limiting script
            script = """
            -- Remove expired tokens
            redis.call('ZREMRANGEBYSCORE', KEYS[1], 0, ARGV[1])

            -- Count remaining tokens
            local count = redis.call('ZCARD', KEYS[1])

            -- Check if under limit
            if count < tonumber(ARGV[3]) then
                -- Add current request
                redis.call('ZADD', KEYS[1], ARGV[2], ARGV[2])
                -- Set expiry to ensure cleanup
                redis.call('EXPIRE', KEYS[1], ARGV[4])
                -- Return remaining
                return {1, tonumber(ARGV[3]) - count - 1, 0}
            else
                -- Get oldest token's timestamp
                local oldest = redis.call('ZRANGE', KEYS[1], 0, 0, 'WITHSCORES')
                -- Calculate reset time
                local reset = tonumber(oldest[2]) + tonumber(ARGV[4]) - tonumber(ARGV[2])
                -- Return not allowed with retry after
                return {0, 0, reset}
            end
            """

            # Execute script
            result = await self.redis.eval(
                script,
                keys=[redis_key],
                args=[window_start, now, limit, window]
            )

            allowed, remaining, retry_after = result
            return bool(allowed), remaining, retry_after

        except Exception as e:
            logger.error(f"Rate limiter error: {str(e)}")
            # Default to allowed in case of errors
            return True, limit - 1, 0

    async def log_request(self, key: str, window: int) -> bool:
        """Log a request without checking limits.

        Args:
            key: Rate limit key (e.g., 'api:flights:search')
            window: Time window in seconds

        Returns:
            True if successful, False otherwise
        """
        try:
            # Current timestamp
            now = int(time.time())

            # Redis key for this rate limit
            redis_key = f"ratelimit:{key}"

            # Add to sorted set
            await self.redis.zadd(redis_key, {now: now})

            # Set expiry
            await self.redis.expire(redis_key, window * 2)

            return True
        except Exception as e:
            logger.error(f"Rate limiter error in log_request: {str(e)}")
            return False

    async def reset_limit(self, key: str) -> bool:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key (e.g., 'api:flights:search')

        Returns:
            True if successful, False otherwise
        """
        try:
            # Redis key for this rate limit
            redis_key = f"ratelimit:{key}"

            # Delete the key
            await self.redis.delete(redis_key)

            return True
        except Exception as e:
            logger.error(f"Rate limiter error in reset_limit: {str(e)}")
            return False

    async def get_usage(self, key: str, window: int) -> Tuple[int, int]:
        """Get current usage for a rate limit key.

        Args:
            key: Rate limit key (e.g., 'api:flights:search')
            window: Time window in seconds

        Returns:
            Tuple of (current_usage, window_remaining_seconds)
        """
        try:
            # Current timestamp
            now = int(time.time())

            # Window start timestamp
            window_start = now - window

            # Redis key for this rate limit
            redis_key = f"ratelimit:{key}"

            # Remove expired tokens
            await self.redis.zremrangebyscore(redis_key, 0, window_start)

            # Count current usage
            count = await self.redis.zcard(redis_key)

            # Get oldest token
            oldest = await self.redis.zrange(redis_key, 0, 0, withscores=True)

            if oldest:
                # Calculate window remaining
                window_remaining = int(oldest[0][1]) + window - now
            else:
                # No tokens, window fully available
                window_remaining = 0

            return count, window_remaining
        except Exception as e:
            logger.error(f"Rate limiter error in get_usage: {str(e)}")
            return 0, 0
```

### 4.2 Integration with MCP Clients

Use the rate limiter in MCP clients:

```python
# src/mcp/flights/client.py (additional methods)
from src.cache.rate_limiter import RateLimiter

# Create rate limiter
rate_limiter = RateLimiter(redis_cache)

# Rate limit configurations
RATE_LIMITS = {
    "SEARCH": {"limit": 120, "window": 60},  # 120 searches per minute
    "DETAILS": {"limit": 240, "window": 60}, # 240 detail lookups per minute
    "ORDER": {"limit": 30, "window": 60}     # 30 orders per minute
}

class FlightsMCPClient(BaseMCPClient):
    # ... existing code ...

    async def _check_rate_limit(self, operation: str) -> bool:
        """Check rate limit for an operation.

        Args:
            operation: Operation name (e.g., 'SEARCH')

        Returns:
            True if allowed, False if rate limited
        """
        if operation not in RATE_LIMITS:
            # No limit defined, allow
            return True

        rate_config = RATE_LIMITS[operation]
        limit_key = f"flights:{operation.lower()}"

        allowed, remaining, retry_after = await rate_limiter.check_limit(
            limit_key,
            rate_config["limit"],
            rate_config["window"]
        )

        if not allowed:
            logger.warning(
                f"Rate limit exceeded for {operation}. "
                f"Retry after {retry_after} seconds."
            )
        else:
            logger.debug(
                f"Rate limit check passed for {operation}. "
                f"Remaining: {remaining}/{rate_config['limit']}"
            )

        return allowed

    @function_tool
    async def search_flights(
        self,
        # ... existing parameters ...
    ) -> Dict[str, Any]:
        """Search for flights between origin and destination."""
        try:
            # Check rate limit first
            if not await self._check_rate_limit("SEARCH"):
                return {
                    "error": "Rate limit exceeded for flight searches. Please try again later.",
                    "rate_limited": True
                }

            # ... existing implementation ...

        except Exception as e:
            # ... existing error handling ...
```

## 5. Cache Monitoring and Management

### 5.1 Cache Health Metrics

Implement cache health monitoring:

```python
# src/cache/monitoring.py
from typing import Dict, Any, List
from datetime import datetime
from src.cache.redis_cache import RedisCache
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class CacheMonitor:
    """Monitoring tools for Redis cache."""

    def __init__(self, redis_cache: RedisCache):
        """Initialize cache monitor.

        Args:
            redis_cache: Redis cache instance
        """
        self.redis = redis_cache

    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary of cache statistics
        """
        try:
            info = await self.redis.info()

            # Extract relevant metrics
            memory_used = info.get("used_memory_human", "N/A")
            total_keys = info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)
            hit_rate = 0
            if total_keys > 0:
                hit_rate = info.get("keyspace_hits", 0) / total_keys * 100

            # Get key counts by namespace
            namespace_counts = await self.get_namespace_counts()

            return {
                "memory_used": memory_used,
                "total_keys": total_keys,
                "hit_rate": hit_rate,
                "namespaces": namespace_counts,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_namespace_counts(self) -> Dict[str, int]:
        """Get key counts by namespace.

        Returns:
            Dictionary of namespace:count pairs
        """
        try:
            namespaces = {
                "flights": "flights:*",
                "hotels": "hotels:*",
                "weather": "weather:*",
                "ratelimit": "ratelimit:*"
            }

            counts = {}
            for name, pattern in namespaces.items():
                count = await self.redis.count_keys(pattern)
                counts[name] = count

            return counts
        except Exception as e:
            logger.error(f"Error getting namespace counts: {str(e)}")
            return {}

    async def get_ttl_distribution(self) -> Dict[str, List[int]]:
        """Get TTL distribution for keys.

        Returns:
            Dictionary of TTL distribution by namespace
        """
        try:
            namespaces = {
                "flights": "flights:*",
                "hotels": "hotels:*",
                "weather": "weather:*"
            }

            distribution = {}
            for name, pattern in namespaces.items():
                ttls = await self._sample_ttls(pattern)
                distribution[name] = ttls

            return distribution
        except Exception as e:
            logger.error(f"Error getting TTL distribution: {str(e)}")
            return {}

    async def _sample_ttls(self, pattern: str, sample_size: int = 100) -> List[int]:
        """Sample TTLs for a pattern.

        Args:
            pattern: Key pattern
            sample_size: Number of keys to sample

        Returns:
            List of TTL values
        """
        try:
            # Get sample of keys
            keys = await self.redis.scan_keys(pattern, sample_size)

            # Get TTLs
            ttls = []
            for key in keys:
                ttl = await self.redis.ttl(key)
                if ttl > 0:  # Ignore keys with no TTL
                    ttls.append(ttl)

            return ttls
        except Exception as e:
            logger.error(f"Error sampling TTLs: {str(e)}")
            return []

    async def purge_namespace(self, namespace: str) -> int:
        """Purge all keys in a namespace.

        Args:
            namespace: Namespace to purge

        Returns:
            Number of keys purged
        """
        try:
            pattern = f"{namespace}:*"
            return await self.redis.delete_pattern(pattern)
        except Exception as e:
            logger.error(f"Error purging namespace {namespace}: {str(e)}")
            return 0
```

### 5.2 Cache Management Controller

Implement a controller for cache management:

```python
# src/cache/controller.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.cache.redis_cache import RedisCache
from src.cache.monitoring import CacheMonitor
from src.utils.logging import get_module_logger

logger = get_module_logger(__name__)

class CacheController:
    """Controller for managing Redis cache."""

    def __init__(self, redis_cache: RedisCache):
        """Initialize cache controller.

        Args:
            redis_cache: Redis cache instance
        """
        self.redis = redis_cache
        self.monitor = CacheMonitor(redis_cache)

    async def clear_cache(self, namespace: Optional[str] = None) -> Dict[str, Any]:
        """Clear cache contents.

        Args:
            namespace: Specific namespace to clear (or all if None)

        Returns:
            Result dictionary
        """
        try:
            if namespace:
                pattern = f"{namespace}:*"
                deleted = await self.redis.delete_pattern(pattern)
                logger.info(f"Cleared {deleted} keys from namespace: {namespace}")
                return {
                    "cleared": deleted,
                    "namespace": namespace,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Clear all namespaces
                namespaces = ["flights", "hotels", "weather", "ratelimit"]
                total_deleted = 0

                for ns in namespaces:
                    pattern = f"{ns}:*"
                    deleted = await self.redis.delete_pattern(pattern)
                    total_deleted += deleted
                    logger.info(f"Cleared {deleted} keys from namespace: {ns}")

                return {
                    "cleared": total_deleted,
                    "namespaces": namespaces,
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error clearing cache: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def reset_cache(self) -> Dict[str, Any]:
        """Reset cache completely.

        Returns:
            Result dictionary
        """
        try:
            await self.redis.flushall()
            logger.info("Reset cache completely")
            return {
                "reset": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error resetting cache: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def get_health(self) -> Dict[str, Any]:
        """Get cache health information.

        Returns:
            Health metrics
        """
        try:
            # Get basic stats
            stats = await self.monitor.get_stats()

            # Get TTL distribution
            ttl_distribution = await self.monitor.get_ttl_distribution()

            # Combine results
            return {
                **stats,
                "ttl_distribution": ttl_distribution,
                "health": await self._assess_health(stats)
            }
        except Exception as e:
            logger.error(f"Error getting cache health: {str(e)}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def _assess_health(self, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Assess cache health from stats.

        Args:
            stats: Cache statistics

        Returns:
            Health assessment
        """
        # Extract memory info
        memory_used = stats.get("memory_used", "N/A")
        hit_rate = stats.get("hit_rate", 0)

        # Assess health criteria
        health = {
            "status": "healthy",
            "issues": []
        }

        # Check hit rate
        if hit_rate < 70:
            health["status"] = "degraded"
            health["issues"].append(f"Low hit rate: {hit_rate:.1f}%")

        # Add more health checks as needed

        return health
```

## 6. Testing the Implementation

### 6.1 Unit Tests for Cache Components

```python
# tests/cache/test_redis_cache.py
import pytest
import asyncio
from unittest.mock import patch, MagicMock
from src.cache.redis_cache import RedisCache

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = MagicMock()
    return redis_mock

@pytest.fixture
def redis_cache(mock_redis):
    """Create Redis cache with mock Redis client."""
    with patch("redis.from_url", return_value=mock_redis):
        cache = RedisCache(url="redis://localhost:6379/0", ttl=60, namespace="test")
        cache._client = mock_redis
        return cache

@pytest.mark.asyncio
async def test_get(redis_cache, mock_redis):
    """Test get method."""
    # Mock Redis get method
    mock_redis.get.return_value = b'{"key": "value"}'

    # Call the method
    result = await redis_cache.get("test_key")

    # Verify
    mock_redis.get.assert_called_once_with("test:test_key")
    assert result == {"key": "value"}

@pytest.mark.asyncio
async def test_get_missing(redis_cache, mock_redis):
    """Test get method with missing key."""
    # Mock Redis get method
    mock_redis.get.return_value = None

    # Call the method
    result = await redis_cache.get("test_key")

    # Verify
    mock_redis.get.assert_called_once_with("test:test_key")
    assert result is None

@pytest.mark.asyncio
async def test_set(redis_cache, mock_redis):
    """Test set method."""
    # Mock Redis setex method
    mock_redis.setex.return_value = True

    # Call the method
    result = await redis_cache.set("test_key", {"key": "value"}, 60)

    # Verify
    mock_redis.setex.assert_called_once()
    assert result is True

@pytest.mark.asyncio
async def test_delete(redis_cache, mock_redis):
    """Test delete method."""
    # Mock Redis delete method
    mock_redis.delete.return_value = 1

    # Call the method
    result = await redis_cache.delete("test_key")

    # Verify
    mock_redis.delete.assert_called_once_with("test:test_key")
    assert result is True

@pytest.mark.asyncio
async def test_cached_decorator(redis_cache):
    """Test cached decorator."""
    # Mock get and set methods
    redis_cache.get = MagicMock(return_value=None)
    redis_cache.set = MagicMock(return_value=True)

    # Define decorated function
    @redis_cache.cached("test_func")
    async def test_func(arg1, arg2=None):
        return {"arg1": arg1, "arg2": arg2}

    # Call the function
    result = await test_func("value1", arg2="value2")

    # Verify
    assert result == {"arg1": "value1", "arg2": "value2"}
    redis_cache.get.assert_called_once()
    redis_cache.set.assert_called_once()
```

### 6.2 Integration Tests for Caching

```python
# tests/mcp/flights/test_client_with_cache.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import date, timedelta
import json

from src.mcp.flights.client import FlightsMCPClient
from src.cache.redis_cache import RedisCache

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis_mock = MagicMock()
    redis_mock.get.return_value = None  # Default to cache miss
    redis_mock.setex.return_value = True
    return redis_mock

@pytest.fixture
def mock_redis_cache(mock_redis):
    """Create mock Redis cache."""
    with patch("src.cache.redis_cache.RedisCache", autospec=True) as mock_cache:
        instance = mock_cache.return_value
        instance.get.return_value = None  # Default to cache miss
        instance.set.return_value = True
        yield instance

@pytest.fixture
def flights_client():
    """Create flights client for testing."""
    return FlightsMCPClient()

@pytest.fixture
def mock_server():
    """Mock MCP server."""
    server_mock = AsyncMock()
    server_mock.invoke_tool = AsyncMock()
    return server_mock

@pytest.mark.asyncio
async def test_search_flights_cache_miss(flights_client, mock_server, mock_redis_cache):
    """Test search_flights with cache miss."""
    # Setup mock server
    with patch.object(flights_client, "get_server", return_value=mock_server):
        # Set up mock response
        mock_response = {
            "offers": [
                {
                    "id": "off_00001",
                    "price": {
                        "amount": 299.99,
                        "currency": "USD"
                    },
                    "airline": {
                        "code": "AA",
                        "name": "American Airlines"
                    }
                }
            ],
            "lowest_price": {
                "amount": 299.99,
                "currency": "USD"
            },
            "total_count": 1
        }

        mock_server.invoke_tool.return_value = mock_response

        # Set up mock cache miss
        with patch("src.mcp.flights.client.redis_cache", mock_redis_cache):
            mock_redis_cache.get.return_value = None

            # Get tomorrow's date
            tomorrow = date.today() + timedelta(days=1)
            next_week = date.today() + timedelta(days=7)

            # Call method
            result = await flights_client.search_flights(
                origin="LAX",
                destination="JFK",
                departure_date=tomorrow,
                return_date=next_week
            )

            # Verify cache was checked
            mock_redis_cache.get.assert_called_once()

            # Verify server was called
            mock_server.invoke_tool.assert_called_once()

            # Verify result matches server response
            assert result == mock_response

            # Verify result was cached
            mock_redis_cache.set.assert_called_once()

@pytest.mark.asyncio
async def test_search_flights_cache_hit(flights_client, mock_server, mock_redis_cache):
    """Test search_flights with cache hit."""
    # Setup mock server (shouldn't be called)
    with patch.object(flights_client, "get_server", return_value=mock_server):
        # Set up mock response in cache
        cached_response = {
            "offers": [
                {
                    "id": "off_00001",
                    "price": {
                        "amount": 299.99,
                        "currency": "USD"
                    }
                }
            ],
            "lowest_price": {
                "amount": 299.99,
                "currency": "USD"
            },
            "total_count": 1,
            "cached": True
        }

        # Set up mock cache hit
        with patch("src.mcp.flights.client.redis_cache", mock_redis_cache):
            mock_redis_cache.get.return_value = cached_response
            mock_redis_cache.get_ttl.return_value = 500  # 500 seconds remaining

            # Get tomorrow's date
            tomorrow = date.today() + timedelta(days=1)
            next_week = date.today() + timedelta(days=7)

            # Call method
            result = await flights_client.search_flights(
                origin="LAX",
                destination="JFK",
                departure_date=tomorrow,
                return_date=next_week
            )

            # Verify cache was checked
            mock_redis_cache.get.assert_called_once()

            # Verify server was NOT called
            mock_server.invoke_tool.assert_not_called()

            # Verify result matches cached response and has cache metadata
            assert result["cached"] is True
            assert "_cache" in result
```

## 7. Monitoring and Metrics

### 7.1 Prometheus Metrics

Set up Prometheus metrics for Redis cache:

```python
# src/cache/metrics.py
import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry

# Create registry
registry = CollectorRegistry()

# Define metrics
cache_hits = Counter(
    "tripsage_cache_hits_total",
    "Total number of cache hits",
    ["namespace", "operation"],
    registry=registry
)

cache_misses = Counter(
    "tripsage_cache_misses_total",
    "Total number of cache misses",
    ["namespace", "operation"],
    registry=registry
)

cache_set_operations = Counter(
    "tripsage_cache_set_operations_total",
    "Total number of cache set operations",
    ["namespace", "operation"],
    registry=registry
)

cache_errors = Counter(
    "tripsage_cache_errors_total",
    "Total number of cache errors",
    ["namespace", "operation", "error_type"],
    registry=registry
)

cache_operation_duration = Histogram(
    "tripsage_cache_operation_duration_seconds",
    "Time spent in cache operations",
    ["namespace", "operation", "result"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=registry
)

cache_item_size = Histogram(
    "tripsage_cache_item_size_bytes",
    "Size of cached items in bytes",
    ["namespace", "operation"],
    buckets=(10, 100, 1000, 10000, 100000, 1000000),
    registry=registry
)

cache_ttl = Histogram(
    "tripsage_cache_ttl_seconds",
    "TTL of cached items in seconds",
    ["namespace", "operation"],
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400, 28800, 86400),
    registry=registry
)

cache_keys_total = Gauge(
    "tripsage_cache_keys_total",
    "Total number of keys in cache",
    ["namespace"],
    registry=registry
)

rate_limit_checks = Counter(
    "tripsage_rate_limit_checks_total",
    "Total number of rate limit checks",
    ["key", "result"],
    registry=registry
)

rate_limit_current = Gauge(
    "tripsage_rate_limit_current",
    "Current rate limit usage",
    ["key"],
    registry=registry
)

class MetricsMiddleware:
    """Middleware for tracking cache metrics."""

    @staticmethod
    async def track_cache_operation(
        namespace: str,
        operation: str,
        start_time: float,
        result: str,
        key: str = None,
        item_size: int = None,
        ttl: int = None,
        error: Exception = None
    ) -> None:
        """Track cache operation metrics.

        Args:
            namespace: Cache namespace
            operation: Operation name (get, set, etc.)
            start_time: Operation start time
            result: Operation result (hit, miss, success, error)
            key: Cache key (optional)
            item_size: Size of item in bytes (optional)
            ttl: TTL in seconds (optional)
            error: Exception if operation failed (optional)
        """
        # Track operation duration
        duration = time.time() - start_time
        cache_operation_duration.labels(namespace, operation, result).observe(duration)

        # Track hit/miss counts
        if operation == "get":
            if result == "hit":
                cache_hits.labels(namespace, operation).inc()
            elif result == "miss":
                cache_misses.labels(namespace, operation).inc()

        # Track set operations
        if operation == "set" and result == "success":
            cache_set_operations.labels(namespace, operation).inc()

        # Track errors
        if result == "error" and error is not None:
            error_type = type(error).__name__
            cache_errors.labels(namespace, operation, error_type).inc()

        # Track item size
        if item_size is not None:
            cache_item_size.labels(namespace, operation).observe(item_size)

        # Track TTL
        if ttl is not None:
            cache_ttl.labels(namespace, operation).observe(ttl)

    @staticmethod
    async def track_rate_limit(key: str, allowed: bool, current: int) -> None:
        """Track rate limit metrics.

        Args:
            key: Rate limit key
            allowed: Whether request was allowed
            current: Current usage count
        """
        result = "allowed" if allowed else "limited"
        rate_limit_checks.labels(key, result).inc()
        rate_limit_current.labels(key).set(current)
```

### 7.2 Redis Cache Health Dashboard

Set up a Redis cache health dashboard:

```python
# src/api/routes/monitoring.py
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any

from src.cache.controller import CacheController
from src.cache.redis_cache import RedisCache
from src.utils.config import REDIS_CONFIG

router = APIRouter()

@router.get("/cache/health")
async def get_cache_health() -> Dict[str, Any]:
    """Get cache health metrics."""
    try:
        redis_cache = RedisCache(
            url=REDIS_CONFIG["URL"],
            ttl=REDIS_CONFIG["DEFAULT_TTL"],
            namespace=REDIS_CONFIG["NAMESPACE"]
        )
        controller = CacheController(redis_cache)
        return await controller.get_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache health: {str(e)}")

@router.post("/cache/clear/{namespace}")
async def clear_cache_namespace(namespace: str) -> Dict[str, Any]:
    """Clear cache for a specific namespace."""
    try:
        redis_cache = RedisCache(
            url=REDIS_CONFIG["URL"],
            ttl=REDIS_CONFIG["DEFAULT_TTL"],
            namespace=REDIS_CONFIG["NAMESPACE"]
        )
        controller = CacheController(redis_cache)
        return await controller.clear_cache(namespace)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@router.post("/cache/reset")
async def reset_cache() -> Dict[str, Any]:
    """Reset cache completely."""
    try:
        redis_cache = RedisCache(
            url=REDIS_CONFIG["URL"],
            ttl=REDIS_CONFIG["DEFAULT_TTL"],
            namespace=REDIS_CONFIG["NAMESPACE"]
        )
        controller = CacheController(redis_cache)
        return await controller.reset_cache()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset cache: {str(e)}")
```

## 8. Deployment Configuration

### 8.1 Docker Compose for Redis

```yaml
# docker-compose.yml (Redis section)
version: "3.8"

services:
  redis:
    image: redis:7.0-alpine
    container_name: tripsage-redis
    command: redis-server /etc/redis/redis.conf
    volumes:
      - ./redis/redis.conf:/etc/redis/redis.conf
      - redis-data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    networks:
      - tripsage-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 1m
      timeout: 10s
      retries: 3
      start_period: 10s

  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: tripsage-redis-commander
    environment:
      - REDIS_HOSTS=redis:redis:6379
    ports:
      - "8081:8081"
    depends_on:
      - redis
    restart: unless-stopped
    networks:
      - tripsage-network

volumes:
  redis-data:

networks:
  tripsage-network:
    driver: bridge
```

### 8.2 Redis Configuration File

```conf
# redis.conf
# Memory management
maxmemory 1gb
maxmemory-policy volatile-ttl
maxmemory-samples 5

# Persistence
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Network
bind 0.0.0.0
protected-mode yes

# Performance
activerehashing yes
lazyfree-lazy-eviction yes
lazyfree-lazy-expire yes
```

## 9. Conclusion

By implementing this comprehensive Redis caching strategy, TripSage can achieve significant performance improvements, reduced API costs, and better user experience. The implementation includes:

1. **Core Redis Caching Infrastructure**: Efficient key storage, serialization, and TTL management
2. **Intelligent TTL Management**: Dynamic TTL based on data volatility and user patterns
3. **Stale-While-Revalidate Pattern**: Improved user experience by serving stale data while refreshing
4. **Rate Limiting**: API quota management to avoid rate limits
5. **Monitoring and Metrics**: Comprehensive metrics for cache health and performance
6. **Testing**: Unit and integration tests for cache functionality

This implementation follows the architectural principles outlined in the CLAUDE.md file, including:

- **KISS** (Keep It Simple, Stupid): Clean, straightforward Redis client implementation
- **DRY** (Don't Repeat Yourself): Reusable cache components
- **YAGNI** (You Aren't Gonna Need It): Focus on essential functionality
- **SOLID** principles: Separation of concerns, interfaces, etc.

The next steps for enhancing this implementation include:

1. Implementing more advanced caching strategies like probabilistic early expiration
2. Adding cache warming capabilities for high-traffic routes and destinations
3. Implementing cross-service cache invalidation for coordinated updates
4. Setting up comprehensive alerting on cache performance degradation

With this implementation in place, TripSage will be able to handle high traffic volumes while maintaining excellent performance and minimizing external API usage costs.
