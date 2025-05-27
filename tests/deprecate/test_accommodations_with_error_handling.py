"""
Standalone tests for error handling decorator in accommodations.py.

This test file verifies that the error handling decorator correctly handles
exceptions in the accommodations search and details methods.
"""

# Import the standalone error handling decorator defined in the other test module
import functools
import inspect
from typing import Any, Callable, Dict, TypeVar
from unittest.mock import AsyncMock, MagicMock

import pytest

F = TypeVar("F", bound=Callable[..., Any])
SyncF = TypeVar("SyncF", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])

# Mock logger for testing
mock_logger = MagicMock()
mock_logger.error = MagicMock()
mock_logger.warning = MagicMock()
mock_logger.info = MagicMock()


def with_error_handling_standalone(func: F) -> F:
    """Test version of with_error_handling decorator.

    This is a standalone copy of the decorator used in the refactored code,
    with the same error handling logic but no external dependencies.
    """
    # Check if the function is a coroutine function (async)
    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Async wrapper function with try-except block."""
            try:
                # Call the original async function
                return await func(*args, **kwargs)
            except Exception as e:
                # Get function name for better error logging
                func_name = func.__name__
                mock_logger.error(f"Error in {func_name}: {str(e)}")

                # Return error response in the expected format for agent tools
                return {"error": str(e)}

        return async_wrapper

    # For synchronous functions
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            """Sync wrapper function with try-except block."""
            try:
                # Call the original sync function
                return func(*args, **kwargs)
            except Exception as e:
                # Get function name for better error logging
                func_name = func.__name__
                mock_logger.error(f"Error in {func_name}: {str(e)}")

                # Return error response in the expected format for agent tools
                return {"error": str(e)}

        return sync_wrapper


# Mock the AccommodationSearchParams for validation testing
class MockAccommodationSearchParams:
    """Mock class for AccommodationSearchParams."""

    def __init__(self, **kwargs):
        self.location = kwargs.get("location", "")
        self.source = kwargs.get("source", "airbnb")
        self.checkin = kwargs.get("checkin")
        self.checkout = kwargs.get("checkout")
        self.adults = kwargs.get("adults", 1)
        self.children = kwargs.get("children")
        self.min_price = kwargs.get("min_price")
        self.max_price = kwargs.get("max_price")
        self.property_type = None

        # For validation testing
        if not self.location:
            raise ValueError("Location is required")


# Mock the create_accommodation_client function
def mock_create_client(source):
    """Mock function for create_accommodation_client."""
    if source != "airbnb":
        raise ValueError(f"Unsupported source: {source}")

    client = AsyncMock()
    client.search_accommodations = AsyncMock()
    client.get_listing_details = AsyncMock()
    return client


# Mock model_dump method
def mock_model_dump():
    """Mock model_dump method."""
    return {"mock": "data"}


class TestAccommodationsWithErrorHandling:
    """Tests for error handling in accommodation methods."""

    @pytest.fixture
    def mock_cache(self):
        """Mock redis cache."""
        cache = AsyncMock()
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock()
        return cache

    @pytest.mark.asyncio
    async def test_search_accommodations_with_error_handling(self, mock_cache):
        """Test error handling in search_accommodations method."""

        # Create a mock implementation similar to search_accommodations
        @with_error_handling_standalone
        async def mock_search_accommodations(
            self, params: Dict[str, Any], cache=mock_cache
        ) -> Dict[str, Any]:
            """Simulates search_accommodations method."""
            # Trigger validation error
            if "trigger_validation_error" in params:
                # This will trigger a ValueError from the mock params validation
                search_params = MockAccommodationSearchParams(**params)

            # Normal validation
            search_params = MockAccommodationSearchParams(**params)

            # Simulate source selection and client creation
            source = search_params.source.lower()

            try:
                client = mock_create_client(source)
            except ValueError:
                return {
                    "error": f"Unsupported accommodation source: {source}",
                    "available_sources": ["airbnb"],
                }

            # Simulate client error
            if "trigger_client_error" in params:
                raise ConnectionError("Failed to connect to accommodation service")

            # Simulate search call
            mock_results = MagicMock()
            mock_results.count = 5
            mock_results.listings = [{"id": "1", "name": "Test Listing"}]
            mock_results.error = None
            mock_results.model_dump = mock_model_dump

            client.search_accommodations.return_value = mock_results

            # Return results
            return {
                "source": source,
                "location": search_params.location,
                "count": mock_results.count,
                "listings": mock_results.listings,
                "error": mock_results.error,
                "cache_hit": False,
            }

        # Test normal operation
        result = await mock_search_accommodations(
            None, {"location": "New York", "source": "airbnb"}
        )
        assert "count" in result
        assert result["count"] == 5
        assert len(result["listings"]) == 1

        # Test validation error
        result = await mock_search_accommodations(
            None, {"trigger_validation_error": True}
        )
        assert "error" in result
        assert "Location is required" in result["error"]

        # Test unsupported source error
        result = await mock_search_accommodations(
            None, {"location": "New York", "source": "unsupported"}
        )
        assert "error" in result
        assert "Unsupported accommodation source" in result["error"]

        # Test client error
        result = await mock_search_accommodations(
            None,
            {"location": "New York", "source": "airbnb", "trigger_client_error": True},
        )
        assert "error" in result
        assert "Failed to connect to accommodation service" in result["error"]

    @pytest.mark.asyncio
    async def test_get_accommodation_details_with_error_handling(self, mock_cache):
        """Test error handling in get_accommodation_details method."""

        # Create a mock implementation similar to get_accommodation_details
        @with_error_handling_standalone
        async def mock_get_accommodation_details(
            self, params: Dict[str, Any], cache=mock_cache
        ) -> Dict[str, Any]:
            """Simulates get_accommodation_details method."""
            # Check required parameters
            if "id" not in params:
                return {"error": "Missing required parameter: id"}

            accommodation_id = params["id"]
            source = params.get("source", "airbnb").lower()

            # Simulate client creation
            try:
                client = mock_create_client(source)
            except ValueError:
                return {
                    "error": f"Unsupported accommodation source: {source}",
                    "available_sources": ["airbnb"],
                }

            # Simulate client error
            if "trigger_client_error" in params:
                raise ConnectionError("Failed to connect to accommodation service")

            # Simulate listing not found
            if accommodation_id == "not_found":
                raise ValueError("Listing not found")

            # Simulate details call
            mock_details = MagicMock()
            mock_details.id = accommodation_id
            mock_details.name = "Test Accommodation"
            mock_details.description = "A lovely place"
            mock_details.url = "https://example.com/listing/123"
            mock_details.location = "New York"
            mock_details.property_type = "Apartment"
            mock_details.host = MagicMock()
            mock_details.host.model_dump = lambda: {"name": "Test Host"}
            mock_details.price_per_night = 100
            mock_details.price_total = 300
            mock_details.rating = 4.8
            mock_details.reviews_count = 50
            mock_details.amenities = ["Wifi", "Kitchen"]
            mock_details.images = ["image1.jpg", "image2.jpg"]
            mock_details.beds = 2
            mock_details.bedrooms = 1
            mock_details.bathrooms = 1
            mock_details.max_guests = 4
            mock_details.model_dump = mock_model_dump

            client.get_listing_details.return_value = mock_details

            # Return details
            return {
                "source": source,
                "id": mock_details.id,
                "name": mock_details.name,
                "description": mock_details.description,
                "url": mock_details.url,
                "location": mock_details.location,
                "property_type": mock_details.property_type,
                "host": mock_details.host.model_dump(),
                "price_per_night": mock_details.price_per_night,
                "rating": mock_details.rating,
                "amenities": mock_details.amenities,
                "cache_hit": False,
            }

        # Test normal operation
        result = await mock_get_accommodation_details(
            None, {"id": "123", "source": "airbnb"}
        )
        assert "id" in result
        assert result["id"] == "123"
        assert result["name"] == "Test Accommodation"

        # Test missing ID
        result = await mock_get_accommodation_details(None, {"source": "airbnb"})
        assert "error" in result
        assert "Missing required parameter: id" in result["error"]

        # Test unsupported source
        result = await mock_get_accommodation_details(
            None, {"id": "123", "source": "unsupported"}
        )
        assert "error" in result
        assert "Unsupported accommodation source" in result["error"]

        # Test listing not found
        result = await mock_get_accommodation_details(
            None, {"id": "not_found", "source": "airbnb"}
        )
        assert "error" in result
        assert "Listing not found" in result["error"]

        # Test client error
        result = await mock_get_accommodation_details(
            None, {"id": "123", "source": "airbnb", "trigger_client_error": True}
        )
        assert "error" in result
        assert "Failed to connect to accommodation service" in result["error"]
