"""
Tests for the Google Maps MCP client.

This module contains tests for the Google Maps MCP client implementation
that interfaces with the Google Maps API.
"""

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.mcp.googlemaps.client import GoogleMapsMCPClient, MCPError
from src.mcp.googlemaps.models import (
    GeocodeParams,
    GeocodeResponse,
)


@pytest.fixture
def config_mock():
    """Mock the config."""
    with patch("src.mcp.googlemaps.client.get_config") as mock:
        mock.return_value = {
            "mcp.googlemaps.endpoint": "http://test-endpoint",
            "mcp.googlemaps.api_key": "test-api-key",
        }
        yield mock


@pytest.fixture
def client(config_mock):
    """Create a test client instance with mocked config."""
    return GoogleMapsMCPClient(
        endpoint="http://test-endpoint",
        api_key="test-api-key",
        use_cache=False,
    )


@pytest.fixture
def mock_geocode_response():
    """Create a mock response for geocode."""
    return {
        "results": [
            {
                "place_id": "ChIJgUbEo8cfqokR5lP9_Wh_DaM",
                "formatted_address": "New York, NY, USA",
                "geometry": {
                    "location": {"lat": 40.7127753, "lng": -74.0059728},
                    "location_type": "APPROXIMATE",
                    "viewport": {
                        "northeast": {"lat": 40.9175771, "lng": -73.70027209999999},
                        "southwest": {"lat": 40.4773991, "lng": -74.25908989999999},
                    },
                },
                "types": ["locality", "political"],
                "address_components": [
                    {
                        "long_name": "New York",
                        "short_name": "New York",
                        "types": ["locality", "political"],
                    },
                    {
                        "long_name": "New York",
                        "short_name": "NY",
                        "types": ["administrative_area_level_1", "political"],
                    },
                    {
                        "long_name": "United States",
                        "short_name": "US",
                        "types": ["country", "political"],
                    },
                ],
            }
        ],
        "status": "OK",
    }


@pytest.fixture
def mock_place_search_response():
    """Create a mock response for place_search."""
    return {
        "results": [
            {
                "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
                "name": "Empire State Building",
                "formatted_address": "20 W 34th St, New York, NY 10001, USA",
                "geometry": {"location": {"lat": 40.7484405, "lng": -73.9856644}},
                "types": ["tourist_attraction", "point_of_interest", "establishment"],
                "rating": 4.7,
                "user_ratings_total": 87575,
                "photos": [
                    {
                        "photo_reference": "photo_reference_value",
                        "width": 4032,
                        "height": 3024,
                    }
                ],
            }
        ],
        "status": "OK",
    }


@pytest.fixture
def mock_place_details_response():
    """Create a mock response for place_details."""
    return {
        "result": {
            "place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "name": "Empire State Building",
            "formatted_address": "20 W 34th St, New York, NY 10001, USA",
            "geometry": {"location": {"lat": 40.7484405, "lng": -73.9856644}},
            "rating": 4.7,
            "website": "https://www.esbnyc.com/",
            "formatted_phone_number": "(212) 736-3100",
            "opening_hours": {
                "weekday_text": [
                    "Monday: 11:00 AM – 11:00 PM",
                    "Tuesday: 11:00 AM – 11:00 PM",
                    "Wednesday: 11:00 AM – 11:00 PM",
                    "Thursday: 11:00 AM – 11:00 PM",
                    "Friday: 11:00 AM – 11:00 PM",
                    "Saturday: 11:00 AM – 11:00 PM",
                    "Sunday: 11:00 AM – 11:00 PM",
                ]
            },
        },
        "status": "OK",
    }


@pytest.fixture
def mock_directions_response():
    """Create a mock response for directions."""
    return {
        "routes": [
            {
                "summary": "I-278 E",
                "legs": [
                    {
                        "distance": {"text": "15.8 mi", "value": 25427},
                        "duration": {"text": "28 mins", "value": 1680},
                        "start_address": "New York, NY, USA",
                        "end_address": "Queens, NY, USA",
                        "steps": [
                            {
                                "distance": {"text": "0.2 mi", "value": 350},
                                "duration": {"text": "1 min", "value": 58},
                                "html_instructions": (
                                    "Head <b>north</b> on <b>Broadway</b>"
                                ),
                                "travel_mode": "DRIVING",
                            }
                        ],
                    }
                ],
                "overview_polyline": {"points": "encoded_polyline_string"},
                "warnings": [],
                "waypoint_order": [],
            }
        ],
        "status": "OK",
    }


@pytest.fixture
def mock_distance_matrix_response():
    """Create a mock response for distance_matrix."""
    return {
        "origin_addresses": ["New York, NY, USA"],
        "destination_addresses": ["Washington, DC, USA", "Boston, MA, USA"],
        "rows": [
            {
                "elements": [
                    {
                        "distance": {"text": "227 mi", "value": 365468},
                        "duration": {"text": "3 hours 54 mins", "value": 14040},
                        "status": "OK",
                    },
                    {
                        "distance": {"text": "215 mi", "value": 346749},
                        "duration": {"text": "3 hours 41 mins", "value": 13260},
                        "status": "OK",
                    },
                ]
            }
        ],
        "status": "OK",
    }


@pytest.fixture
def mock_elevation_response():
    """Create a mock response for elevation."""
    return {
        "results": [
            {
                "elevation": 8.883694648742676,
                "location": {"lat": 40.7127753, "lng": -74.0059728},
                "resolution": 4.771975994110107,
            }
        ],
        "status": "OK",
    }


class TestGoogleMapsMCPClient:
    """Tests for the GoogleMapsMCPClient class."""

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_geocode(self, mock_call_tool, client, mock_geocode_response):
        """Test geocoding an address."""
        mock_call_tool.return_value = mock_geocode_response

        # Test with valid address
        result = await client.geocode("New York")

        # Verify call_tool parameters
        mock_call_tool.assert_called_once_with(
            "maps_geocode", {"address": "New York"}, False
        )

        # Verify result
        assert isinstance(result, dict)  # In practice, this would be a GeocodeResponse
        assert result["status"] == "OK"
        assert len(result["results"]) == 1
        assert result["results"][0]["formatted_address"] == "New York, NY, USA"
        assert result["results"][0]["geometry"]["location"]["lat"] == 40.7127753
        assert result["results"][0]["geometry"]["location"]["lng"] == -74.0059728

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_geocode_validation_error(self, mock_call_tool, client):
        """Test validation error handling for geocode."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError", exc_info={"address": ["Address can't be empty"]}
        )

        # Test with empty address
        with pytest.raises(MCPError) as exc_info:
            await client.geocode("")

        assert "Invalid parameters" in str(exc_info.value)

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_geocode_api_error(self, mock_call_tool, client):
        """Test API error handling for geocode."""
        # Simulate API error
        mock_call_tool.side_effect = Exception("API error")

        # Test with API error
        with pytest.raises(MCPError) as exc_info:
            await client.geocode("Invalid Address")

        assert "Geocoding failed" in str(exc_info.value)

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_reverse_geocode(self, mock_call_tool, client, mock_geocode_response):
        """Test reverse geocoding coordinates."""
        mock_call_tool.return_value = mock_geocode_response

        # Test with valid coordinates
        result = await client.reverse_geocode(40.7127753, -74.0059728)

        # Verify call_tool parameters
        mock_call_tool.assert_called_once_with(
            "maps_reverse_geocode", {"lat": 40.7127753, "lng": -74.0059728}, False
        )

        # Verify result
        assert isinstance(result, dict)
        assert result["status"] == "OK"
        assert len(result["results"]) == 1
        assert result["results"][0]["formatted_address"] == "New York, NY, USA"

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_place_search(
        self, mock_call_tool, client, mock_place_search_response
    ):
        """Test searching for places."""
        mock_call_tool.return_value = mock_place_search_response

        # Test with valid query and location
        result = await client.place_search(
            query="Empire State Building",
            location="New York",
            radius=5000,
            type="tourist_attraction",
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]

        # Verify tool parameters
        assert call_args[0] == "maps_search_places"
        params = call_args[1]
        assert params["query"] == "Empire State Building"
        assert params["location"] == "New York"
        assert params["radius"] == 5000
        assert params["type"] == "tourist_attraction"

        # Verify result
        assert isinstance(result, dict)
        assert result["status"] == "OK"
        assert len(result["results"]) == 1
        assert result["results"][0]["name"] == "Empire State Building"
        assert result["results"][0]["rating"] == 4.7

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_place_details(
        self, mock_call_tool, client, mock_place_details_response
    ):
        """Test getting place details."""
        mock_call_tool.return_value = mock_place_details_response

        # Test with valid place_id
        result = await client.place_details("ChIJN1t_tDeuEmsRUsoyG83frY4")

        # Verify call_tool parameters
        mock_call_tool.assert_called_once_with(
            "maps_place_details", {"place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4"}, False
        )

        # Verify result
        assert isinstance(result, dict)
        assert result["status"] == "OK"
        assert result["result"]["name"] == "Empire State Building"
        assert (
            result["result"]["formatted_address"]
            == "20 W 34th St, New York, NY 10001, USA"
        )
        assert result["result"]["website"] == "https://www.esbnyc.com/"

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_directions(self, mock_call_tool, client, mock_directions_response):
        """Test getting directions."""
        mock_call_tool.return_value = mock_directions_response

        # Test with valid parameters
        result = await client.directions(
            origin="New York",
            destination="Queens",
            mode="driving",
            waypoints=["Brooklyn Bridge"],
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]

        # Verify tool parameters are validated by Pydantic
        assert call_args[0] == "maps_directions"
        params = call_args[1]
        assert params["origin"] == "New York"
        assert params["destination"] == "Queens"
        assert params["mode"] == "driving"
        assert params["waypoints"] == ["Brooklyn Bridge"]

        # Verify result
        assert isinstance(result, dict)
        assert result["status"] == "OK"
        assert len(result["routes"]) == 1
        assert result["routes"][0]["summary"] == "I-278 E"
        assert result["routes"][0]["legs"][0]["distance"]["text"] == "15.8 mi"
        assert result["routes"][0]["legs"][0]["duration"]["text"] == "28 mins"

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_distance_matrix(
        self, mock_call_tool, client, mock_distance_matrix_response
    ):
        """Test getting distance matrix."""
        mock_call_tool.return_value = mock_distance_matrix_response

        # Test with valid parameters
        result = await client.distance_matrix(
            origins=["New York"],
            destinations=["Washington, DC", "Boston"],
            mode="driving",
        )

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]

        # Verify tool parameters are validated by Pydantic
        assert call_args[0] == "maps_distance_matrix"
        params = call_args[1]
        assert params["origins"] == ["New York"]
        assert params["destinations"] == ["Washington, DC", "Boston"]
        assert params["mode"] == "driving"

        # Verify result
        assert isinstance(result, dict)
        assert result["status"] == "OK"
        assert result["origin_addresses"] == ["New York, NY, USA"]
        assert result["destination_addresses"] == [
            "Washington, DC, USA",
            "Boston, MA, USA",
        ]
        assert result["rows"][0]["elements"][0]["distance"]["text"] == "227 mi"
        assert result["rows"][0]["elements"][1]["distance"]["text"] == "215 mi"

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test_elevation(self, mock_call_tool, client, mock_elevation_response):
        """Test getting elevation data."""
        mock_call_tool.return_value = mock_elevation_response

        # Test with valid locations
        locations = [{"lat": 40.7127753, "lng": -74.0059728}]
        result = await client.elevation(locations)

        # Verify call_tool parameters
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]

        # Verify tool parameters are validated by Pydantic
        assert call_args[0] == "maps_elevation"
        params = call_args[1]
        assert params["locations"] == ["40.7127753,-74.0059728"]

        # Verify result
        assert isinstance(result, dict)
        assert result["status"] == "OK"
        assert len(result["results"]) == 1
        assert result["results"][0]["elevation"] == 8.883694648742676
        assert result["results"][0]["location"]["lat"] == 40.7127753
        assert result["results"][0]["location"]["lng"] == -74.0059728

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test__call_validate_tool(
        self, mock_call_tool, client, mock_geocode_response
    ):
        """Test the _call_validate_tool method directly."""
        mock_call_tool.return_value = mock_geocode_response

        # Create valid parameters
        params = GeocodeParams(address="New York")

        # Test with valid parameters and response model
        result = await client._call_validate_tool(
            "maps_geocode", params, GeocodeResponse
        )

        # Verify parameters were dumped correctly
        mock_call_tool.assert_called_once()
        call_args = mock_call_tool.call_args[0]
        assert call_args[0] == "maps_geocode"
        assert isinstance(call_args[1], dict)
        assert call_args[1]["address"] == "New York"

        # Verify result was validated
        assert isinstance(result, dict)  # In practice, this would be a GeocodeResponse
        assert result["status"] == "OK"
        assert len(result["results"]) == 1

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test__call_validate_tool_validation_error(self, mock_call_tool, client):
        """Test validation error handling in _call_validate_tool."""
        # Simulate validation error
        mock_call_tool.side_effect = ValidationError.from_exception_data(
            title="ValidationError", exc_info={"address": ["Address can't be empty"]}
        )

        # Create invalid parameters
        params = GeocodeParams(address="")

        # Test with invalid parameters
        with pytest.raises(MCPError) as exc_info:
            await client._call_validate_tool("maps_geocode", params, GeocodeResponse)

        assert "Invalid parameters" in str(exc_info.value)

    @patch("src.mcp.googlemaps.client.BaseMCPClient.call_tool")
    async def test__call_validate_tool_response_validation_error(
        self, mock_call_tool, client
    ):
        """Test response validation error handling in _call_validate_tool."""
        # Create an invalid response (missing required fields)
        mock_call_tool.return_value = {"invalid": "response"}

        # Create valid parameters
        params = GeocodeParams(address="New York")

        # Test with valid parameters but invalid response
        result = await client._call_validate_tool(
            "maps_geocode", params, GeocodeResponse
        )

        # Should still return a result even though validation failed
        assert result == {"invalid": "response"}
