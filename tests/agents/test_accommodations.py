"""
Tests for the accommodation agent tools.

These tests verify the behavior of the accommodation search tool wrappers
and their interaction with MCP clients.
"""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from src.agents.accommodations import (
    AccommodationSearchTool,
    search_airbnb_rentals,
    get_airbnb_listing_details,
    search_accommodations,
)
from src.mcp.accommodations.models import AirbnbSearchResult, AirbnbListingDetails

# Test data
TEST_LOCATION = "San Francisco, CA"
TEST_LISTING_ID = "12345678"


@pytest.fixture
def mock_airbnb_search_results():
    """Mock Airbnb search results."""
    return {
        "location": TEST_LOCATION,
        "count": 2,
        "listings": [
            {
                "id": "12345678",
                "name": "Cozy apartment in downtown",
                "url": "https://www.airbnb.com/rooms/12345678",
                "price_string": "$150 per night",
                "price_total": 1050,
                "rating": 4.8,
                "location_info": "Downtown, San Francisco",
                "property_type": "Apartment",
            },
            {
                "id": "87654321",
                "name": "Luxury condo with bay views",
                "url": "https://www.airbnb.com/rooms/87654321",
                "price_string": "$250 per night",
                "price_total": 1750,
                "rating": 4.9,
                "location_info": "Nob Hill, San Francisco",
                "property_type": "Condominium",
            },
        ],
        "error": None,
    }


@pytest.fixture
def mock_airbnb_listing_details():
    """Mock Airbnb listing details."""
    return {
        "id": TEST_LISTING_ID,
        "name": "Cozy apartment in downtown",
        "description": "A beautiful apartment in downtown SF",
        "url": f"https://www.airbnb.com/rooms/{TEST_LISTING_ID}",
        "location": "Downtown, San Francisco",
        "property_type": "Apartment",
        "host": {
            "name": "John",
            "superhost": True,
        },
        "price_per_night": 150,
        "price_total": 1050,
        "rating": 4.8,
        "reviews_count": 120,
        "amenities": ["Wifi", "Kitchen"],
        "images": ["https://example.com/image1.jpg"],
        "beds": 2,
        "bedrooms": 1,
        "bathrooms": 1,
        "max_guests": 4,
    }


class TestAccommodationTool:
    """Tests for the AccommodationSearchTool class."""

    @patch("src.agents.accommodations.create_accommodation_client")
    @patch("src.agents.accommodations.redis_cache.get")
    async def test_search_accommodations_airbnb(
        self, mock_cache_get, mock_create_client, mock_airbnb_search_results
    ):
        """Test searching for Airbnb accommodations."""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_client = MagicMock()
        mock_client.search_accommodations = AsyncMock(
            return_value=AirbnbSearchResult.model_validate(mock_airbnb_search_results)
        )
        mock_create_client.return_value = mock_client

        # Create the tool and call search_accommodations
        tool = AccommodationSearchTool()
        result = await tool.search_accommodations(
            {
                "location": TEST_LOCATION,
                "source": "airbnb",
                "adults": 2,
            }
        )

        # Verify client was created with the right source
        mock_create_client.assert_called_once_with("airbnb")

        # Verify search was called with correct parameters
        mock_client.search_accommodations.assert_called_once()
        call_args = mock_client.search_accommodations.call_args[1]
        assert call_args["location"] == TEST_LOCATION
        assert call_args["adults"] == 2

        # Verify result
        assert result["source"] == "airbnb"
        assert result["location"] == TEST_LOCATION
        assert result["count"] == 2
        assert len(result["listings"]) == 2
        assert result["listings"][0]["name"] == "Cozy apartment in downtown"
        assert result["listings"][1]["name"] == "Luxury condo with bay views"

    @patch("src.agents.accommodations.create_accommodation_client")
    @patch("src.agents.accommodations.redis_cache.get")
    async def test_get_accommodation_details_airbnb(
        self, mock_cache_get, mock_create_client, mock_airbnb_listing_details
    ):
        """Test getting Airbnb accommodation details."""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_client = MagicMock()
        mock_client.get_listing_details = AsyncMock(
            return_value=AirbnbListingDetails.model_validate(mock_airbnb_listing_details)
        )
        mock_create_client.return_value = mock_client

        # Create the tool and call get_accommodation_details
        tool = AccommodationSearchTool()
        result = await tool.get_accommodation_details(
            {
                "id": TEST_LISTING_ID,
                "source": "airbnb",
                "adults": 2,
            }
        )

        # Verify client was created with the right source
        mock_create_client.assert_called_once_with("airbnb")

        # Verify get_listing_details was called with correct parameters
        mock_client.get_listing_details.assert_called_once()
        call_args = mock_client.get_listing_details.call_args[1]
        assert call_args["listing_id"] == TEST_LISTING_ID
        assert call_args["adults"] == 2

        # Verify result
        assert result["source"] == "airbnb"
        assert result["id"] == TEST_LISTING_ID
        assert result["name"] == "Cozy apartment in downtown"
        assert result["description"] == "A beautiful apartment in downtown SF"
        assert result["property_type"] == "Apartment"

    @patch("src.agents.accommodations.create_accommodation_client")
    @patch("src.agents.accommodations.redis_cache.get")
    async def test_search_accommodations_unsupported_source(
        self, mock_cache_get, mock_create_client
    ):
        """Test searching with an unsupported accommodation source."""
        # Setup mocks
        mock_cache_get.return_value = None
        mock_create_client.side_effect = ValueError("Unsupported accommodation source: invalid")

        # Create the tool and call search_accommodations
        tool = AccommodationSearchTool()
        result = await tool.search_accommodations(
            {
                "location": TEST_LOCATION,
                "source": "invalid",
            }
        )

        # Verify error response
        assert "error" in result
        assert "Unsupported accommodation source" in result["error"]
        assert "available_sources" in result
        assert "message" in result

    @patch("src.agents.accommodations.redis_cache.get")
    async def test_search_accommodations_missing_id(self, mock_cache_get):
        """Test getting accommodation details without an ID."""
        # Setup mocks
        mock_cache_get.return_value = None

        # Create the tool and call get_accommodation_details without ID
        tool = AccommodationSearchTool()
        result = await tool.get_accommodation_details({})

        # Verify error response
        assert "error" in result
        assert "Missing required parameter: id" in result["error"]


class TestAccommodationFunctions:
    """Tests for the accommodation function tools."""

    @patch("src.agents.accommodations.accommodation_tool.search_accommodations")
    async def test_search_airbnb_rentals(
        self, mock_search_accommodations, mock_airbnb_search_results
    ):
        """Test the search_airbnb_rentals function."""
        # Setup mock
        mock_search_accommodations.return_value = mock_airbnb_search_results

        # Call function
        result = await search_airbnb_rentals(
            location=TEST_LOCATION,
            adults=2,
            min_price=100,
            max_price=300,
        )

        # Verify search_accommodations was called with right parameters
        mock_search_accommodations.assert_called_once()
        call_args = mock_search_accommodations.call_args[0][0]
        assert call_args["location"] == TEST_LOCATION
        assert call_args["source"] == "airbnb"
        assert call_args["adults"] == 2
        assert call_args["min_price"] == 100
        assert call_args["max_price"] == 300

        # Verify result
        assert result == mock_airbnb_search_results

    @patch("src.agents.accommodations.accommodation_tool.get_accommodation_details")
    async def test_get_airbnb_listing_details(
        self, mock_get_details, mock_airbnb_listing_details
    ):
        """Test the get_airbnb_listing_details function."""
        # Setup mock
        mock_get_details.return_value = mock_airbnb_listing_details

        # Call function
        result = await get_airbnb_listing_details(
            listing_id=TEST_LISTING_ID,
            adults=2,
        )

        # Verify get_accommodation_details was called with right parameters
        mock_get_details.assert_called_once()
        call_args = mock_get_details.call_args[0][0]
        assert call_args["id"] == TEST_LISTING_ID
        assert call_args["source"] == "airbnb"
        assert call_args["adults"] == 2

        # Verify result
        assert result == mock_airbnb_listing_details

    @patch("src.agents.accommodations.accommodation_tool.search_accommodations")
    async def test_search_accommodations(
        self, mock_search_accommodations, mock_airbnb_search_results
    ):
        """Test the generic search_accommodations function."""
        # Setup mock
        mock_search_accommodations.return_value = mock_airbnb_search_results

        # Call function with explicit source
        result = await search_accommodations(
            location=TEST_LOCATION,
            source="airbnb",
            adults=2,
        )

        # Verify search_accommodations was called with right parameters
        mock_search_accommodations.assert_called_once()
        call_args = mock_search_accommodations.call_args[0][0]
        assert call_args["location"] == TEST_LOCATION
        assert call_args["source"] == "airbnb"
        assert call_args["adults"] == 2

        # Verify result
        assert result == mock_airbnb_search_results