"""
Tests for the Google Maps MCP client.

This module contains tests for the GoogleMapsMCPClient class, which interacts with
the Google Maps MCP server to provide geocoding, directions, place search, and other
Google Maps API services.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tripsage.clients.maps.google_maps_mcp_client import GoogleMapsMCPClient
from tripsage.tools.schemas.googlemaps import (
    GeocodeResponse,
)
from tripsage.utils.cache import ContentType, WebOperationsCache
from tripsage.utils.error_handling import MCPError


@pytest.fixture
async def mock_httpx_client():
    """Create a mock httpx client for testing."""
    mock_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(return_value={"status": "OK", "results": []})
    mock_client.post = AsyncMock(return_value=mock_response)
    return mock_client


@pytest.fixture
async def mock_web_cache():
    """Create a mock web cache for testing."""
    mock_cache = AsyncMock(spec=WebOperationsCache)
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    mock_cache.generate_cache_key = MagicMock(return_value="test-cache-key")
    return mock_cache


@pytest.fixture
async def google_maps_client(mock_httpx_client, mock_web_cache):
    """Create a Google Maps MCP client for testing."""
    # Reset the singleton instance
    GoogleMapsMCPClient._instance = None

    with patch("httpx.AsyncClient", return_value=mock_httpx_client):
        with patch.object(WebOperationsCache, "__new__", return_value=mock_web_cache):
            client = GoogleMapsMCPClient(
                endpoint="https://test-endpoint.example.com",
                api_key="test-api-key",
            )
            await client.connect()
            yield client
            await client.disconnect()


@pytest.mark.asyncio
async def test_geocode(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test geocoding an address."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "results": [
                {
                    "place_id": "test-place-id",
                    "formatted_address": "123 Test St, Test City, TS 12345",
                    "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}},
                    "address_components": [],
                    "types": ["street_address"],
                }
            ],
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.geocode(address="123 Test St")

    # Check the result
    assert result.status == "OK"
    assert len(result.results) == 1
    assert result.results[0].place_id == "test-place-id"
    assert result.results[0].formatted_address == "123 Test St, Test City, TS 12345"

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/geocode", json={"address": "123 Test St"}
    )

    # Check that caching was attempted
    mock_web_cache.get.assert_called_once()
    mock_web_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_reverse_geocode(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test reverse geocoding coordinates."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "results": [
                {
                    "place_id": "test-place-id",
                    "formatted_address": "123 Test St, Test City, TS 12345",
                    "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}},
                    "address_components": [],
                    "types": ["street_address"],
                }
            ],
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.reverse_geocode(lat=37.4224764, lng=-122.0842499)

    # Check the result
    assert result.status == "OK"
    assert len(result.results) == 1
    assert result.results[0].place_id == "test-place-id"
    assert result.results[0].formatted_address == "123 Test St, Test City, TS 12345"

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/reverse_geocode", json={"lat": 37.4224764, "lng": -122.0842499}
    )


@pytest.mark.asyncio
async def test_place_search(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test searching for places."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "results": [
                {
                    "place_id": "test-place-id",
                    "name": "Test Restaurant",
                    "formatted_address": "123 Test St, Test City, TS 12345",
                    "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}},
                    "types": ["restaurant", "food"],
                    "price_level": 2,
                    "rating": 4.5,
                    "user_ratings_total": 100,
                    "vicinity": "123 Test St",
                }
            ],
            "next_page_token": None,
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.place_search(
        query="restaurants", location="37.4224764,-122.0842499", radius=1000
    )

    # Check the result
    assert result.status == "OK"
    assert len(result.results) == 1
    assert result.results[0].place_id == "test-place-id"
    assert result.results[0].name == "Test Restaurant"
    assert result.results[0].rating == 4.5

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/place_search",
        json={
            "query": "restaurants",
            "location": "37.4224764,-122.0842499",
            "radius": 1000,
        },
    )


@pytest.mark.asyncio
async def test_place_details(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test getting place details."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "result": {
                "place_id": "test-place-id",
                "name": "Test Restaurant",
                "formatted_address": "123 Test St, Test City, TS 12345",
                "geometry": {"location": {"lat": 37.4224764, "lng": -122.0842499}},
                "types": ["restaurant", "food"],
                "price_level": 2,
                "rating": 4.5,
                "user_ratings_total": 100,
                "formatted_phone_number": "555-1234",
                "website": "https://example.com",
                "opening_hours": {
                    "weekday_text": [
                        "Monday: 9:00 AM – 10:00 PM",
                        "Tuesday: 9:00 AM – 10:00 PM",
                    ]
                },
            },
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.place_details(place_id="test-place-id")

    # Check the result
    assert result.status == "OK"
    assert result.result is not None
    assert result.result["place_id"] == "test-place-id"
    assert result.result["name"] == "Test Restaurant"
    assert result.result["rating"] == 4.5

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/place_details", json={"place_id": "test-place-id"}
    )


@pytest.mark.asyncio
async def test_directions(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test getting directions."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "routes": [
                {
                    "summary": "Test Route",
                    "legs": [
                        {
                            "start_address": "123 Test St, Test City, TS 12345",
                            "end_address": "456 Sample Ave, Test City, TS 12345",
                            "distance": {"text": "5 km", "value": 5000},
                            "duration": {"text": "10 mins", "value": 600},
                            "steps": [
                                {
                                    "html_instructions": "Head <b>north</b> on Test St",
                                    "distance": {"text": "1 km", "value": 1000},
                                    "duration": {"text": "2 mins", "value": 120},
                                }
                            ],
                        }
                    ],
                    "overview_polyline": {"points": "test_polyline"},
                    "warnings": [],
                    "waypoint_order": [],
                    "fare": None,
                }
            ],
            "geocoded_waypoints": [],
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.directions(
        origin="123 Test St, Test City",
        destination="456 Sample Ave, Test City",
        mode="driving",
    )

    # Check the result
    assert result.status == "OK"
    assert len(result.routes) == 1
    assert result.routes[0].summary == "Test Route"
    assert len(result.routes[0].legs) == 1
    assert result.routes[0].legs[0]["distance"]["text"] == "5 km"

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/directions",
        json={
            "origin": "123 Test St, Test City",
            "destination": "456 Sample Ave, Test City",
            "mode": "driving",
        },
    )


@pytest.mark.asyncio
async def test_distance_matrix(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test getting distance matrix."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "origin_addresses": ["123 Test St, Test City, TS 12345"],
            "destination_addresses": [
                "456 Sample Ave, Test City, TS 12345",
                "789 Example Rd, Test City, TS 12345",
            ],
            "rows": [
                {
                    "elements": [
                        {
                            "status": "OK",
                            "distance": {"text": "5 km", "value": 5000},
                            "duration": {"text": "10 mins", "value": 600},
                        },
                        {
                            "status": "OK",
                            "distance": {"text": "10 km", "value": 10000},
                            "duration": {"text": "20 mins", "value": 1200},
                        },
                    ]
                }
            ],
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.distance_matrix(
        origins=["123 Test St, Test City"],
        destinations=["456 Sample Ave, Test City", "789 Example Rd, Test City"],
        mode="driving",
    )

    # Check the result
    assert result.status == "OK"
    assert len(result.origin_addresses) == 1
    assert len(result.destination_addresses) == 2
    assert len(result.rows) == 1
    assert len(result.rows[0]["elements"]) == 2
    assert result.rows[0]["elements"][0]["distance"]["text"] == "5 km"

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/distance_matrix",
        json={
            "origins": ["123 Test St, Test City"],
            "destinations": ["456 Sample Ave, Test City", "789 Example Rd, Test City"],
            "mode": "driving",
        },
    )


@pytest.mark.asyncio
async def test_timezone(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test getting timezone information."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "dstOffset": 3600,
            "rawOffset": -28800,
            "timeZoneId": "America/Los_Angeles",
            "timeZoneName": "Pacific Daylight Time",
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.timezone(location="37.4224764,-122.0842499")

    # Check the result
    assert result.status == "OK"
    assert result.timeZoneId == "America/Los_Angeles"
    assert result.timeZoneName == "Pacific Daylight Time"
    assert result.dstOffset == 3600
    assert result.rawOffset == -28800

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/timezone", json={"location": "37.4224764,-122.0842499"}
    )


@pytest.mark.asyncio
async def test_elevation(google_maps_client, mock_httpx_client, mock_web_cache):
    """Test getting elevation data."""
    # Mock the response
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock()
    mock_response.json = AsyncMock(
        return_value={
            "status": "OK",
            "results": [
                {
                    "elevation": 100.0,
                    "resolution": 10.0,
                    "location": {"lat": 37.4224764, "lng": -122.0842499},
                },
                {
                    "elevation": 200.0,
                    "resolution": 10.0,
                    "location": {"lat": 37.5, "lng": -122.5},
                },
            ],
        }
    )
    mock_httpx_client.post.return_value = mock_response

    # Call the method
    result = await google_maps_client.elevation(
        locations=["37.4224764,-122.0842499", "37.5,-122.5"]
    )

    # Check the result
    assert result.status == "OK"
    assert len(result.results) == 2
    assert result.results[0]["elevation"] == 100.0
    assert result.results[1]["elevation"] == 200.0

    # Check the request
    mock_httpx_client.post.assert_called_once_with(
        "/elevation", json={"locations": ["37.4224764,-122.0842499", "37.5,-122.5"]}
    )


@pytest.mark.asyncio
async def test_error_handling(google_maps_client, mock_httpx_client):
    """Test that errors are properly caught and formatted."""
    # Mock the response to raise an error
    mock_response = AsyncMock()
    mock_response.raise_for_status = AsyncMock(side_effect=Exception("Test error"))
    mock_httpx_client.post.return_value = mock_response

    # Call the method (should not raise exception due to error handling)
    with pytest.raises(MCPError):
        await google_maps_client._call_mcp(
            tool_name="geocode",
            params={"address": "123 Test St"},
            response_model=GeocodeResponse,
            content_type=ContentType.SEMI_STATIC,
        )

    # Check the request was made
    mock_httpx_client.post.assert_called_once_with(
        "/geocode", json={"address": "123 Test St"}
    )
