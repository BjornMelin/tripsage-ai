"""
Integration tests for the Airbnb MCP client.

These tests verify that the Airbnb MCP client correctly interacts with
the Airbnb MCP server to search for accommodations and retrieve listing details.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from tripsage.mcp.accommodations.client import AirbnbMCPClient
from tripsage.mcp.accommodations.models import AirbnbListingDetails, AirbnbSearchResult
from tripsage.utils.error_handling import MCPError

# Test data
TEST_LOCATION = "San Francisco, CA"
TEST_LISTING_ID = "12345678"
TOMORROW = (date.today() + timedelta(days=1)).isoformat()
DAYS_LATER = (date.today() + timedelta(days=8)).isoformat()


@pytest.fixture
def client():
    """Create a test client instance."""
    return AirbnbMCPClient(
        endpoint="http://test-endpoint",
        server_type="openbnb/mcp-server-airbnb",
        use_cache=False,
    )


@pytest.fixture
def mock_search_response():
    """Mock response for search accommodations."""
    return {
        "location": TEST_LOCATION,
        "count": 2,
        "listings": [
            {
                "id": "12345678",
                "name": "Cozy apartment in downtown",
                "url": "https://www.airbnb.com/rooms/12345678",
                "image": "https://example.com/image1.jpg",
                "superhost": True,
                "price_string": "$150 per night",
                "price_total": 1050,
                "rating": 4.8,
                "reviews_count": 120,
                "location_info": "Downtown, San Francisco",
                "property_type": "Apartment",
                "beds": 2,
                "bedrooms": 1,
                "bathrooms": 1,
            },
            {
                "id": "87654321",
                "name": "Luxury condo with bay views",
                "url": "https://www.airbnb.com/rooms/87654321",
                "image": "https://example.com/image2.jpg",
                "superhost": False,
                "price_string": "$250 per night",
                "price_total": 1750,
                "rating": 4.9,
                "reviews_count": 85,
                "location_info": "Nob Hill, San Francisco",
                "property_type": "Condominium",
                "beds": 3,
                "bedrooms": 2,
                "bathrooms": 2,
            },
        ],
    }


@pytest.fixture
def mock_listing_details_response():
    """Mock response for listing details."""
    return {
        "id": TEST_LISTING_ID,
        "url": f"https://www.airbnb.com/rooms/{TEST_LISTING_ID}",
        "name": "Cozy apartment in downtown",
        "description": "Beautiful apartment located in the heart of downtown.",
        "host": {
            "name": "John Doe",
            "image": "https://example.com/host.jpg",
            "superhost": True,
        },
        "property_type": "Apartment",
        "location": "Downtown, San Francisco",
        "coordinates": {"lat": 37.7749, "lng": -122.4194},
        "amenities": ["WiFi", "Kitchen", "Washer", "Dryer", "Free parking"],
        "bedrooms": 1,
        "beds": 2,
        "bathrooms": 1,
        "max_guests": 4,
        "rating": 4.8,
        "reviews_count": 120,
        "reviews_summary": [
            {"category": "Cleanliness", "rating": 4.9},
            {"category": "Communication", "rating": 5.0},
            {"category": "Check-in", "rating": 4.7},
        ],
        "price_per_night": 150,
        "price_total": 1050,
        "images": [
            "https://example.com/image1.jpg",
            "https://example.com/image2.jpg",
            "https://example.com/image3.jpg",
        ],
    }


class TestAirbnbMCPClient:
    """Tests for the AirbnbMCPClient class."""

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_search_accommodations_basic(
        self, mock_call_tool, client, mock_search_response
    ):
        """Test basic accommodation search with minimal parameters."""
        mock_call_tool.return_value = mock_search_response

        # Mock storage methods to avoid actual DB/memory calls
        client._store_search_results = AsyncMock()

        result = await client.search_accommodations(location=TEST_LOCATION)

        # Verify call_tool was called with correct parameters
        mock_call_tool.assert_called_once_with(
            "airbnb_search", {"location": TEST_LOCATION}, False
        )

        # Check response is correct Pydantic model instance
        assert isinstance(result, AirbnbSearchResult)
        assert result.location == TEST_LOCATION
        assert result.count == 2
        assert len(result.listings) == 2
        assert result.listings[0].name == "Cozy apartment in downtown"
        assert result.listings[1].name == "Luxury condo with bay views"

        # Verify storage method was called
        client._store_search_results.assert_called_once()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_search_accommodations_with_filters(
        self, mock_call_tool, client, mock_search_response
    ):
        """Test accommodation search with filters."""
        mock_call_tool.return_value = mock_search_response

        # Mock storage methods to avoid actual DB/memory calls
        client._store_search_results = AsyncMock()

        result = await client.search_accommodations(
            location=TEST_LOCATION,
            checkin=TOMORROW,
            checkout=DAYS_LATER,
            adults=2,
            children=1,
            min_price=100,
            max_price=300,
        )

        # Verify call_tool was called with correct parameters
        mock_call_tool.assert_called_once_with(
            "airbnb_search",
            {
                "location": TEST_LOCATION,
                "checkin": TOMORROW,
                "checkout": DAYS_LATER,
                "adults": 2,
                "children": 1,
                "minPrice": 100,
                "maxPrice": 300,
            },
            False,
        )

        # Check response
        assert isinstance(result, AirbnbSearchResult)
        assert result.count == 2
        assert len(result.listings) == 2

        # Verify storage method was called
        client._store_search_results.assert_called_once()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_search_accommodations_with_store_results_false(
        self, mock_call_tool, client, mock_search_response
    ):
        """Test accommodation search with store_results=False."""
        mock_call_tool.return_value = mock_search_response

        # Mock storage methods to avoid actual DB/memory calls
        client._store_search_results = AsyncMock()

        result = await client.search_accommodations(
            location=TEST_LOCATION,
            store_results=False,
        )

        # Verify call_tool was called with correct parameters
        mock_call_tool.assert_called_once_with(
            "airbnb_search", {"location": TEST_LOCATION}, False
        )

        # Check response
        assert isinstance(result, AirbnbSearchResult)

        # Verify storage method was NOT called
        client._store_search_results.assert_not_called()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_search_accommodations_error_handling(self, mock_call_tool, client):
        """Test error handling in accommodation search."""
        mock_call_tool.side_effect = Exception("API error")

        # Mock storage methods to avoid actual DB/memory calls
        client._store_search_results = AsyncMock()

        result = await client.search_accommodations(location=TEST_LOCATION)

        # Check error response
        assert isinstance(result, AirbnbSearchResult)
        assert result.count == 0
        assert len(result.listings) == 0
        assert result.error is not None
        assert "API error" in result.error

        # Verify storage method was NOT called
        client._store_search_results.assert_not_called()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_get_listing_details(
        self, mock_call_tool, client, mock_listing_details_response
    ):
        """Test basic listing details retrieval."""
        mock_call_tool.return_value = mock_listing_details_response

        # Mock storage methods to avoid actual DB/memory calls
        client._store_listing_details = AsyncMock()

        result = await client.get_listing_details(listing_id=TEST_LISTING_ID)

        # Verify call_tool was called with correct parameters
        mock_call_tool.assert_called_once_with(
            "airbnb_listing_details", {"id": TEST_LISTING_ID}, False
        )

        # Check response is correct Pydantic model instance
        assert isinstance(result, AirbnbListingDetails)
        assert result.id == TEST_LISTING_ID
        assert result.name == "Cozy apartment in downtown"
        assert result.property_type == "Apartment"
        assert len(result.amenities) == 5
        assert result.price_per_night == 150

        # Verify storage method was called
        client._store_listing_details.assert_called_once()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_get_listing_details_with_params(
        self, mock_call_tool, client, mock_listing_details_response
    ):
        """Test listing details retrieval with date parameters."""
        mock_call_tool.return_value = mock_listing_details_response

        # Mock storage methods to avoid actual DB/memory calls
        client._store_listing_details = AsyncMock()

        result = await client.get_listing_details(
            listing_id=TEST_LISTING_ID, checkin=TOMORROW, checkout=DAYS_LATER, adults=2
        )

        # Verify call_tool was called with correct parameters
        mock_call_tool.assert_called_once_with(
            "airbnb_listing_details",
            {
                "id": TEST_LISTING_ID,
                "checkin": TOMORROW,
                "checkout": DAYS_LATER,
                "adults": 2,
            },
            False,
        )

        # Check response
        assert isinstance(result, AirbnbListingDetails)
        assert result.id == TEST_LISTING_ID
        assert result.price_total == 1050

        # Verify storage method was called
        client._store_listing_details.assert_called_once()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_get_listing_details_with_store_results_false(
        self, mock_call_tool, client, mock_listing_details_response
    ):
        """Test listing details retrieval with store_results=False."""
        mock_call_tool.return_value = mock_listing_details_response

        # Mock storage methods to avoid actual DB/memory calls
        client._store_listing_details = AsyncMock()

        result = await client.get_listing_details(
            listing_id=TEST_LISTING_ID,
            store_results=False,
        )

        # Verify call_tool was called with correct parameters
        mock_call_tool.assert_called_once_with(
            "airbnb_listing_details", {"id": TEST_LISTING_ID}, False
        )

        # Check response
        assert isinstance(result, AirbnbListingDetails)

        # Verify storage method was NOT called
        client._store_listing_details.assert_not_called()

    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_get_listing_details_error(self, mock_call_tool, client):
        """Test error handling in listing details retrieval."""
        mock_call_tool.side_effect = MCPError(
            message="Failed to get listing details",
            server="http://test-endpoint",
            tool="airbnb_listing_details",
            params={"id": TEST_LISTING_ID},
        )

        with pytest.raises(MCPError):
            await client.get_listing_details(listing_id=TEST_LISTING_ID)

    async def test_date_conversion(self, client):
        """Test date object conversion to string."""
        with patch(
            "src.mcp.accommodations.client.BaseMCPClient.call_tool"
        ) as mock_call_tool:
            mock_call_tool.return_value = {"listings": []}

            # Mock storage methods to avoid actual DB/memory calls
            client._store_search_results = AsyncMock()

            today = date.today()
            next_week = today + timedelta(days=7)

            await client.search_accommodations(
                location=TEST_LOCATION, checkin=today, checkout=next_week
            )

            # Verify date objects were converted to ISO format strings
            call_args = mock_call_tool.call_args[0][1]
            assert call_args["checkin"] == today.isoformat()
            assert call_args["checkout"] == next_week.isoformat()

    # Parametrized tests for search parameters
    @pytest.mark.parametrize(
        "param_name,param_value,expected_key",
        [
            ("min_price", 100, "minPrice"),
            ("max_price", 300, "maxPrice"),
            ("min_beds", 2, "minBeds"),
            ("min_bedrooms", 2, "minBedrooms"),
            ("min_bathrooms", 2, "minBathrooms"),
            ("property_type", "apartment", "propertyType"),
            ("room_type", "entire_home", "roomType"),
            ("place_id", "ChIJIQBpAG2ahYAR_6128GcTUEo", "placeId"),
            ("ignore_robots_txt", True, "ignoreRobotsText"),
        ],
    )
    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_parameter_mapping(
        self, mock_call_tool, client, param_name, param_value, expected_key
    ):
        """Test parameter mapping for various search parameters."""
        mock_call_tool.return_value = {"listings": []}
        client._store_search_results = AsyncMock()

        # Build dynamic parameters
        params = {"location": TEST_LOCATION, param_name: param_value}
        await client.search_accommodations(**params)

        # Get parameters passed to call_tool
        call_args = mock_call_tool.call_args[0][1]

        # Verify the parameter was mapped correctly
        assert expected_key in call_args
        assert call_args[expected_key] == param_value
        assert param_name not in call_args

    # Parametrized tests for validation errors
    @pytest.mark.parametrize(
        "param_name,invalid_value,error_substring",
        [
            # These tests would pass with the updated client.py that
            # handles ValidationError
            ("adults", 0, "Input should be greater than or equal to 1"),
            ("adults", 20, "Input should be less than or equal to 16"),
            ("children", -1, "Input should be greater than or equal to 0"),
            ("location", "", "Input should have at least 1 character"),
        ],
    )
    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_validation_errors(
        self, mock_call_tool, client, param_name, invalid_value, error_substring
    ):
        """Test parameter validation errors."""
        # Build dynamic parameters with an invalid value
        params = {"location": TEST_LOCATION}
        params[param_name] = invalid_value

        # If testing the location parameter, update default
        if param_name == "location":
            params["location"] = invalid_value

        # With the updated client.py that has the ValidationError handler
        with pytest.raises(MCPError) as exc_info:
            await client.search_accommodations(**params)

        # Verify the error message contains the expected text
        assert error_substring in str(exc_info.value)

        # Ensure the call_tool was never called
        mock_call_tool.assert_not_called()

    # Edge cases for search parameters
    @pytest.mark.parametrize(
        "search_kwargs",
        [
            # Empty search parameters
            {},
            # Maximum allowed values
            {"adults": 16, "children": 10, "infants": 5, "pets": 3},
            # All parameters provided
            {
                "location": TEST_LOCATION,
                "place_id": "ChIJIQBpAG2ahYAR_6128GcTUEo",
                "checkin": TOMORROW,
                "checkout": DAYS_LATER,
                "adults": 2,
                "children": 1,
                "infants": 1,
                "pets": 1,
                "min_price": 100,
                "max_price": 500,
                "min_beds": 2,
                "min_bedrooms": 1,
                "min_bathrooms": 1,
                "property_type": "apartment",
                "amenities": ["wifi", "pool"],
                "room_type": "entire_home",
                "superhost": True,
                "cursor": "abc123",
                "ignore_robots_txt": True,
            },
        ],
    )
    @patch("src.mcp.accommodations.client.BaseMCPClient.call_tool")
    async def test_search_edge_cases(self, mock_call_tool, client, search_kwargs):
        """Test search with various parameter combinations."""
        # Ensure location is always present
        if "location" not in search_kwargs:
            search_kwargs["location"] = TEST_LOCATION

        mock_call_tool.return_value = {"listings": []}
        client._store_search_results = AsyncMock()

        # Should not raise any exception
        await client.search_accommodations(**search_kwargs)

        # Verify call_tool was called
        mock_call_tool.assert_called_once()

    @patch("src.mcp.accommodations.client.get_db_client")
    @patch("src.mcp.accommodations.client.memory_client")
    async def test_store_search_results(
        self, mock_memory_client, mock_db_client, client, mock_search_response
    ):
        """Test storing search results in database and memory."""
        # Setup mock database client
        mock_accommodations_repo = AsyncMock()
        mock_db_client.return_value.accommodations = mock_accommodations_repo

        # Setup mock memory client
        mock_memory_client.create_entities = AsyncMock()

        # Create a search result to store
        search_result = AirbnbSearchResult.model_validate(mock_search_response)

        # Call the method
        await client._store_search_results(
            search_result=search_result,
            checkin=TOMORROW,
            checkout=DAYS_LATER,
        )

        # Verify database calls
        assert mock_accommodations_repo.create_or_update.call_count == 2

        # Verify memory calls
        mock_memory_client.create_entities.assert_called_once()

    @patch("src.mcp.accommodations.client.get_db_client")
    @patch("src.mcp.accommodations.client.memory_client")
    async def test_store_listing_details(
        self, mock_memory_client, mock_db_client, client, mock_listing_details_response
    ):
        """Test storing listing details in database and memory."""
        # Setup mock database client
        mock_accommodations_repo = AsyncMock()
        mock_db_client.return_value.accommodations = mock_accommodations_repo

        # Setup mock memory client
        mock_memory_client.create_entities = AsyncMock()
        mock_memory_client.create_relations = AsyncMock()

        # Create a listing details to store
        listing_details = AirbnbListingDetails.model_validate(
            mock_listing_details_response
        )

        # Call the method
        await client._store_listing_details(
            listing_details=listing_details,
            checkin=TOMORROW,
            checkout=DAYS_LATER,
        )

        # Verify database calls
        mock_accommodations_repo.create_or_update.assert_called_once()

        # Verify memory calls
        mock_memory_client.create_entities.assert_called_once()
        mock_memory_client.create_relations.assert_called_once()
