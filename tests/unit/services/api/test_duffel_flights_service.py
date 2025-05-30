"""Tests for Duffel Flights service implementation."""

import json
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import pytest_asyncio
from pydantic import ValidationError

from tripsage.models.api.flights_models import (
    Airline,
    CabinClass,
    FlightOffer,
    Passenger,
    PassengerType,
    PaymentRequest,
    Segment,
    Slice,
)
from tripsage_core.services.external_apis.duffel_http_client import DuffelHTTPClient


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock()
    settings.DUFFEL_API_TOKEN = "test_api_token"
    settings.DUFFEL_TEST_MODE = True
    return settings


@pytest.fixture
def mock_redis():
    """Mock Redis service."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.keys = AsyncMock(return_value=[])
    redis.sadd = AsyncMock()
    return redis


@pytest_asyncio.fixture
async def flights_service(mock_settings, mock_redis):
    """Create flights service instance for testing."""
    with patch(
        "tripsage_core.services.external_apis.duffel_http_client.settings",
        mock_settings,
    ):
        service = DuffelHTTPClient()
        service.redis = mock_redis
        return service


@pytest.mark.asyncio
async def test_duffel_service_context_manager(flights_service):
    """Test async context manager functionality."""
    async with flights_service as service:
        assert service is not None
        assert hasattr(service, "client")


class TestDuffelHTTPClient:
    """Test cases for Duffel Flights service."""

    @pytest.mark.asyncio
    async def test_init_with_token(self, mock_settings):
        """Test service initialization with API token."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.settings",
            mock_settings,
        ):
            service = DuffelHTTPClient()
            assert service.api_token == "test_api_token"
            assert service.test_mode is True
            assert service.base_url == "https://api.duffel.com"

    @pytest.mark.asyncio
    async def test_init_without_token(self):
        """Test service initialization without API token."""
        with patch(
            "tripsage_core.services.external_apis.duffel_http_client.settings"
        ) as mock_settings:
            mock_settings.DUFFEL_API_TOKEN = None
            with pytest.raises(ValueError, match="DUFFEL_API_TOKEN not configured"):
                DuffelHTTPClient()

    @pytest.mark.asyncio
    async def test_search_airports(self, flights_service, httpx_mock):
        """Test searching for airports."""
        # Mock API response
        mock_response = {
            "data": [
                {
                    "id": "arp_jfk_us",
                    "type": "airport",
                    "iata_code": "JFK",
                    "name": "John F. Kennedy International Airport",
                    "city_name": "New York",
                    "country_name": "United States",
                    "latitude": 40.6413,
                    "longitude": -73.7781,
                    "time_zone": "America/New_York",
                },
                {
                    "id": "arp_lga_us",
                    "type": "airport",
                    "iata_code": "LGA",
                    "name": "LaGuardia Airport",
                    "city_name": "New York",
                    "country_name": "United States",
                    "latitude": 40.7769,
                    "longitude": -73.8740,
                    "time_zone": "America/New_York",
                },
            ]
        }

        httpx_mock.add_response(
            url="https://api.duffel.com/places/suggestions?query=New+York&limit=10&appid=test_api_token",
            json=mock_response,
        )

        airports = await flights_service.search_airports("New York")

        assert len(airports) == 2
        assert airports[0].iata_code == "JFK"
        assert airports[0].name == "John F. Kennedy International Airport"
        assert airports[1].iata_code == "LGA"

    @pytest.mark.asyncio
    async def test_search_flights(self, flights_service, httpx_mock):
        """Test searching for flights."""
        # Mock offer request response
        offer_request_response = {
            "data": {
                "id": "orq_123",
                "offers": [
                    {
                        "id": "off_123",
                        "total_amount": "250.00",
                        "total_currency": "USD",
                        "owner": {
                            "id": "arl_123",
                            "iata_code": "AA",
                            "name": "American Airlines",
                        },
                        "slices": [
                            {
                                "id": "sli_123",
                                "segments": [
                                    {
                                        "id": "seg_123",
                                        "operating_carrier": {
                                            "id": "arl_123",
                                            "iata_code": "AA",
                                            "name": "American Airlines",
                                        },
                                        "marketing_carrier": {
                                            "id": "arl_123",
                                            "iata_code": "AA",
                                            "name": "American Airlines",
                                        },
                                        "operating_carrier_flight_number": "100",
                                        "marketing_carrier_flight_number": "100",
                                        "departing_at": (
                                            datetime.now() + timedelta(days=1)
                                        ).isoformat()
                                        + "Z",
                                        "arriving_at": (
                                            datetime.now() + timedelta(days=1, hours=3)
                                        ).isoformat()
                                        + "Z",
                                        "duration": "PT3H",
                                    }
                                ],
                            }
                        ],
                        "passengers": [{"id": "pas_123", "type": "adult"}],
                    }
                ],
            }
        }

        httpx_mock.add_response(
            method="POST",
            url="https://api.duffel.com/offer_requests",
            json=offer_request_response,
        )

        offers = await flights_service.search_flights(
            origin="JFK",
            destination="LAX",
            departure_date=datetime.now() + timedelta(days=1),
            cabin_class=CabinClass.economy,
        )

        assert len(offers) == 1
        assert offers[0].id == "off_123"
        assert offers[0].total_amount == "250.00"
        assert offers[0].owner.iata_code == "AA"

    @pytest.mark.asyncio
    async def test_search_flights_round_trip(self, flights_service, httpx_mock):
        """Test searching for round trip flights."""
        mock_response = {
            "data": {
                "id": "orq_456",
                "offers": [
                    {
                        "id": "off_456",
                        "total_amount": "500.00",
                        "total_currency": "USD",
                        "owner": {
                            "id": "arl_456",
                            "iata_code": "UA",
                            "name": "United Airlines",
                        },
                        "slices": [
                            {
                                "id": "sli_456",
                                "segments": [
                                    {
                                        "id": "seg_456",
                                        "operating_carrier": {
                                            "id": "arl_456",
                                            "iata_code": "UA",
                                            "name": "United Airlines",
                                        },
                                        "marketing_carrier": {
                                            "id": "arl_456",
                                            "iata_code": "UA",
                                            "name": "United Airlines",
                                        },
                                        "operating_carrier_flight_number": "200",
                                        "departing_at": (
                                            datetime.now() + timedelta(days=1)
                                        ).isoformat()
                                        + "Z",
                                        "arriving_at": (
                                            datetime.now() + timedelta(days=1, hours=5)
                                        ).isoformat()
                                        + "Z",
                                        "duration": "PT5H",
                                    }
                                ],
                            },
                            {
                                "id": "sli_789",
                                "segments": [
                                    {
                                        "id": "seg_789",
                                        "operating_carrier": {
                                            "id": "arl_456",
                                            "iata_code": "UA",
                                            "name": "United Airlines",
                                        },
                                        "marketing_carrier": {
                                            "id": "arl_456",
                                            "iata_code": "UA",
                                            "name": "United Airlines",
                                        },
                                        "operating_carrier_flight_number": "201",
                                        "departing_at": (
                                            datetime.now() + timedelta(days=7)
                                        ).isoformat()
                                        + "Z",
                                        "arriving_at": (
                                            datetime.now() + timedelta(days=7, hours=5)
                                        ).isoformat()
                                        + "Z",
                                        "duration": "PT5H",
                                    }
                                ],
                            },
                        ],
                        "passengers": [{"id": "pas_456", "type": "adult"}],
                    }
                ],
            }
        }

        httpx_mock.add_response(
            method="POST",
            url="https://api.duffel.com/offer_requests",
            json=mock_response,
        )

        offers = await flights_service.search_flights(
            origin="NYC",
            destination="LAX",
            departure_date=datetime.now() + timedelta(days=1),
            return_date=datetime.now() + timedelta(days=7),
        )

        assert len(offers) == 1
        assert len(offers[0].slices) == 2  # Round trip has 2 slices

    @pytest.mark.asyncio
    async def test_get_offer_details(self, flights_service, httpx_mock):
        """Test getting detailed offer information."""
        mock_response = {
            "data": {
                "id": "off_123",
                "total_amount": "250.00",
                "total_currency": "USD",
                "tax_amount": "50.00",
                "base_amount": "200.00",
                "owner": {
                    "id": "arl_123",
                    "iata_code": "AA",
                    "name": "American Airlines",
                },
                "slices": [
                    {
                        "id": "sli_123",
                        "segments": [
                            {
                                "id": "seg_123",
                                "operating_carrier": {
                                    "id": "arl_123",
                                    "iata_code": "AA",
                                    "name": "American Airlines",
                                },
                                "departing_at": datetime.now().isoformat() + "Z",
                                "arriving_at": (
                                    datetime.now() + timedelta(hours=3)
                                ).isoformat()
                                + "Z",
                                "duration": "PT3H",
                            }
                        ],
                    }
                ],
                "passengers": [{"id": "pas_123", "type": "adult"}],
                "conditions": {
                    "refundable_before_departure": False,
                    "changeable_before_departure": True,
                },
            }
        }

        httpx_mock.add_response(
            url="https://api.duffel.com/offers/off_123",
            json=mock_response,
        )

        offer = await flights_service.get_offer_details("off_123")

        assert offer.id == "off_123"
        assert offer.total_amount == "250.00"
        assert offer.tax_amount == "50.00"
        assert offer.base_amount == "200.00"

    @pytest.mark.asyncio
    async def test_create_order(self, flights_service, httpx_mock):
        """Test creating a flight order."""
        passengers = [
            Passenger(
                type=PassengerType.adult,
                given_name="John",
                family_name="Doe",
                email="john.doe@example.com",
                phone_number="+1234567890",
                born_on=date(1990, 1, 1),
            )
        ]

        payment = PaymentRequest(
            type="balance",
            amount=250.00,
            currency="USD",
        )

        mock_response = {
            "data": {
                "id": "ord_123",
                "booking_reference": "ABC123",
                "total_amount": "250.00",
                "total_currency": "USD",
                "status": "confirmed",
                "owner": {
                    "id": "arl_123",
                    "iata_code": "AA",
                    "name": "American Airlines",
                },
                "slices": [
                    {
                        "id": "sli_123",
                        "segments": [
                            {
                                "id": "seg_123",
                                "operating_carrier": {
                                    "id": "arl_123",
                                    "iata_code": "AA",
                                    "name": "American Airlines",
                                },
                                "departing_at": datetime.now().isoformat() + "Z",
                                "arriving_at": (
                                    datetime.now() + timedelta(hours=3)
                                ).isoformat()
                                + "Z",
                            }
                        ],
                    }
                ],
                "passengers": [
                    {
                        "id": "pas_123",
                        "type": "adult",
                        "given_name": "John",
                        "family_name": "Doe",
                    }
                ],
            }
        }

        httpx_mock.add_response(
            method="POST",
            url="https://api.duffel.com/orders",
            json=mock_response,
        )

        order = await flights_service.create_order(
            offer_id="off_123",
            passengers=passengers,
            payment=payment,
        )

        assert order.id == "ord_123"
        assert order.booking_reference == "ABC123"
        assert order.status == "confirmed"

    @pytest.mark.asyncio
    async def test_get_order(self, flights_service, httpx_mock):
        """Test getting order details."""
        mock_response = {
            "data": {
                "id": "ord_123",
                "booking_reference": "ABC123",
                "total_amount": "250.00",
                "total_currency": "USD",
                "status": "confirmed",
                "created_at": datetime.now().isoformat() + "Z",
                "owner": {
                    "id": "arl_123",
                    "iata_code": "AA",
                    "name": "American Airlines",
                },
                "slices": [],
                "passengers": [],
            }
        }

        httpx_mock.add_response(
            url="https://api.duffel.com/orders/ord_123",
            json=mock_response,
        )

        order = await flights_service.get_order("ord_123")

        assert order.id == "ord_123"
        assert order.booking_reference == "ABC123"
        assert order.status == "confirmed"

    @pytest.mark.asyncio
    async def test_list_orders(self, flights_service, httpx_mock):
        """Test listing orders with filters."""
        mock_response = {
            "data": [
                {
                    "id": "ord_123",
                    "booking_reference": "ABC123",
                    "total_amount": "250.00",
                    "total_currency": "USD",
                    "status": "confirmed",
                    "created_at": datetime.now().isoformat() + "Z",
                    "owner": {
                        "id": "arl_123",
                        "iata_code": "AA",
                        "name": "American Airlines",
                    },
                    "slices": [],
                    "passengers": [],
                },
                {
                    "id": "ord_456",
                    "booking_reference": "DEF456",
                    "total_amount": "350.00",
                    "total_currency": "USD",
                    "status": "confirmed",
                    "created_at": (datetime.now() - timedelta(days=1)).isoformat()
                    + "Z",
                    "owner": {
                        "id": "arl_456",
                        "iata_code": "UA",
                        "name": "United Airlines",
                    },
                    "slices": [],
                    "passengers": [],
                },
            ]
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.duffel.com/orders",
                params={"limit": "50", "appid": "test_api_token"},
            ),
            json=mock_response,
        )

        orders = await flights_service.list_orders()

        assert len(orders) == 2
        assert orders[0].id == "ord_123"
        assert orders[1].id == "ord_456"

    @pytest.mark.asyncio
    async def test_cancel_order(self, flights_service, httpx_mock):
        """Test cancelling an order."""
        mock_response = {
            "data": {
                "id": "orc_123",
                "order_id": "ord_123",
                "created_at": datetime.now().isoformat() + "Z",
                "confirmed_at": datetime.now().isoformat() + "Z",
                "refund_amount": "200.00",
                "refund_currency": "USD",
            }
        }

        httpx_mock.add_response(
            method="POST",
            url="https://api.duffel.com/order_cancellations",
            json=mock_response,
        )

        cancellation = await flights_service.cancel_order("ord_123")

        assert cancellation.id == "orc_123"
        assert cancellation.order_id == "ord_123"
        assert cancellation.refund_amount == "200.00"

    @pytest.mark.asyncio
    async def test_get_seat_maps(self, flights_service, httpx_mock):
        """Test getting seat maps for an offer."""
        mock_response = {
            "data": [
                {
                    "id": "sea_123",
                    "segment_id": "seg_123",
                    "aircraft": {
                        "id": "arc_123",
                        "name": "Boeing 737-800",
                        "iata_code": "738",
                    },
                    "cabins": [
                        {
                            "cabin_class": "economy",
                            "rows": [
                                {
                                    "number": 1,
                                    "seats": [
                                        {
                                            "id": "seat_1A",
                                            "row": 1,
                                            "column": "A",
                                            "available": True,
                                            "type": "seat",
                                        },
                                        {
                                            "id": "seat_1B",
                                            "row": 1,
                                            "column": "B",
                                            "available": False,
                                            "type": "seat",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                }
            ]
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.duffel.com/seat_maps",
                params={"offer_id": "off_123", "appid": "test_api_token"},
            ),
            json=mock_response,
        )

        seat_maps = await flights_service.get_seat_maps("off_123")

        assert len(seat_maps) == 1
        assert seat_maps[0].segment_id == "seg_123"
        assert seat_maps[0].aircraft

    @pytest.mark.asyncio
    async def test_search_flexible_dates(self, flights_service, httpx_mock):
        """Test searching flights with flexible dates."""
        base_date = datetime.now() + timedelta(days=30)

        # Mock responses for multiple date searches
        for i in range(-3, 4):  # -3 to +3 days
            mock_response = {
                "data": {
                    "id": f"orq_{i}",
                    "offers": [
                        {
                            "id": f"off_{i}",
                            "total_amount": f"{200 + i * 10}.00",
                            "total_currency": "USD",
                            "owner": {
                                "id": "arl_123",
                                "iata_code": "AA",
                                "name": "American Airlines",
                            },
                            "slices": [],
                            "passengers": [],
                        }
                    ],
                }
            }
            httpx_mock.add_response(
                method="POST",
                url="https://api.duffel.com/offer_requests",
                json=mock_response,
            )

        results = await flights_service.search_flexible_dates(
            origin="JFK",
            destination="LAX",
            departure_date=base_date,
            flexibility_days=3,
        )

        assert len(results) == 7  # -3 to +3 days
        for _date_str, offers in results.items():
            assert isinstance(offers, list)

    @pytest.mark.asyncio
    async def test_find_cheapest_offer(self, flights_service):
        """Test finding the cheapest offer from a list."""
        offers = [
            FlightOffer(
                id="off_1",
                total_amount="300.00",
                total_currency="USD",
                owner=Airline(id="arl_1", iata_code="AA", name="American"),
                slices=[
                    Slice(
                        id="sli_1",
                        segments=[
                            Segment(
                                id="seg_1",
                                departing_at=(
                                    datetime.now() + timedelta(hours=1)
                                ).isoformat()
                                + "Z",
                                arriving_at=(
                                    datetime.now() + timedelta(hours=4)
                                ).isoformat()
                                + "Z",
                            )
                        ],
                    )
                ],
                passengers=[],
            ),
            FlightOffer(
                id="off_2",
                total_amount="250.00",
                total_currency="USD",
                owner=Airline(id="arl_2", iata_code="UA", name="United"),
                slices=[
                    Slice(
                        id="sli_2",
                        segments=[
                            Segment(
                                id="seg_2",
                                departing_at=(
                                    datetime.now() + timedelta(hours=2)
                                ).isoformat()
                                + "Z",
                                arriving_at=(
                                    datetime.now() + timedelta(hours=5)
                                ).isoformat()
                                + "Z",
                            )
                        ],
                    )
                ],
                passengers=[],
            ),
            FlightOffer(
                id="off_3",
                total_amount="280.00",
                total_currency="USD",
                owner=Airline(id="arl_3", iata_code="DL", name="Delta"),
                slices=[
                    Slice(
                        id="sli_3",
                        segments=[
                            Segment(
                                id="seg_3",
                                departing_at=(
                                    datetime.now() + timedelta(hours=3)
                                ).isoformat()
                                + "Z",
                                arriving_at=(
                                    datetime.now() + timedelta(hours=6)
                                ).isoformat()
                                + "Z",
                            ),
                            Segment(
                                id="seg_4",
                                departing_at=(
                                    datetime.now() + timedelta(hours=7)
                                ).isoformat()
                                + "Z",
                                arriving_at=(
                                    datetime.now() + timedelta(hours=10)
                                ).isoformat()
                                + "Z",
                            ),
                        ],
                    )
                ],
                passengers=[],
            ),
        ]

        # Find cheapest without constraints
        cheapest = await flights_service.find_cheapest_offer(offers)
        assert cheapest.id == "off_2"
        assert cheapest.total_amount == "250.00"

        # Find cheapest with max stops constraint
        cheapest_direct = await flights_service.find_cheapest_offer(offers, max_stops=0)
        assert cheapest_direct.id == "off_2"  # off_3 has 1 stop

        # Find cheapest with duration constraint
        cheapest_short = await flights_service.find_cheapest_offer(
            offers, max_duration_hours=3.5
        )
        assert cheapest_short.id == "off_2"

    @pytest.mark.asyncio
    async def test_airline_preferences(self, flights_service):
        """Test filtering offers by airline preferences."""
        offers = [
            FlightOffer(
                id="off_1",
                total_amount="300.00",
                total_currency="USD",
                owner=Airline(id="arl_1", iata_code="AA", name="American"),
                slices=[
                    Slice(
                        id="sli_1",
                        segments=[
                            Segment(
                                id="seg_1",
                                operating_carrier=Airline(
                                    id="arl_1", iata_code="AA", name="American"
                                ),
                                marketing_carrier=Airline(
                                    id="arl_1", iata_code="AA", name="American"
                                ),
                                departing_at=datetime.now().isoformat() + "Z",
                                arriving_at=(
                                    datetime.now() + timedelta(hours=3)
                                ).isoformat()
                                + "Z",
                            )
                        ],
                    )
                ],
                passengers=[],
            ),
            FlightOffer(
                id="off_2",
                total_amount="250.00",
                total_currency="USD",
                owner=Airline(id="arl_2", iata_code="UA", name="United"),
                slices=[
                    Slice(
                        id="sli_2",
                        segments=[
                            Segment(
                                id="seg_2",
                                operating_carrier=Airline(
                                    id="arl_2", iata_code="UA", name="United"
                                ),
                                marketing_carrier=Airline(
                                    id="arl_2", iata_code="UA", name="United"
                                ),
                                departing_at=datetime.now().isoformat() + "Z",
                                arriving_at=(
                                    datetime.now() + timedelta(hours=3)
                                ).isoformat()
                                + "Z",
                            )
                        ],
                    )
                ],
                passengers=[],
            ),
        ]

        # Test preferred airlines
        filtered = await flights_service.get_airline_preferences(
            offers,
            preferred_airlines={"AA"},
        )
        assert len(filtered) == 1
        assert filtered[0].id == "off_1"

        # Test excluded airlines
        filtered = await flights_service.get_airline_preferences(
            offers,
            excluded_airlines={"UA"},
        )
        assert len(filtered) == 1
        assert filtered[0].id == "off_1"

    @pytest.mark.asyncio
    async def test_create_trip_booking(self, flights_service, httpx_mock):
        """Test creating a booking for a trip."""
        lead_passenger = Passenger(
            type=PassengerType.adult,
            given_name="Jane",
            family_name="Smith",
            email="jane.smith@example.com",
            phone_number="+1234567890",
            born_on=date(1985, 5, 15),
        )

        mock_response = {
            "data": {
                "id": "ord_trip123",
                "booking_reference": "TRIP123",
                "total_amount": "500.00",
                "total_currency": "USD",
                "status": "confirmed",
                "owner": {
                    "id": "arl_123",
                    "iata_code": "AA",
                    "name": "American Airlines",
                },
                "slices": [],
                "passengers": [
                    {
                        "id": "pas_trip123",
                        "type": "adult",
                        "given_name": "Jane",
                        "family_name": "Smith",
                        "metadata": {"trip_id": "trip_123"},
                    }
                ],
            }
        }

        httpx_mock.add_response(
            method="POST",
            url="https://api.duffel.com/orders",
            json=mock_response,
        )

        order = await flights_service.create_trip_booking(
            offer_id="off_123",
            trip_id="trip_123",
            lead_passenger=lead_passenger,
        )

        assert order.id == "ord_trip123"
        assert order.booking_reference == "TRIP123"

    @pytest.mark.asyncio
    async def test_error_handling(self, flights_service, httpx_mock):
        """Test error handling for API failures."""
        # Test 404 error
        httpx_mock.add_response(
            url="https://api.duffel.com/offers/nonexistent",
            status_code=404,
            json={
                "errors": [
                    {
                        "type": "invalid_request_error",
                        "title": "Not found",
                        "message": "The requested resource could not be found",
                        "code": "not_found",
                    }
                ]
            },
        )

        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            await flights_service.get_offer_details("nonexistent")

        assert exc_info.value.response.status_code == 404

    @pytest.mark.asyncio
    async def test_caching_behavior(self, flights_service, mock_redis, httpx_mock):
        """Test caching for airport searches."""
        mock_response = {
            "data": [
                {
                    "id": "arp_lax_us",
                    "type": "airport",
                    "iata_code": "LAX",
                    "name": "Los Angeles International Airport",
                    "city_name": "Los Angeles",
                    "country_name": "United States",
                    "latitude": 33.9425,
                    "longitude": -118.4081,
                    "time_zone": "America/Los_Angeles",
                }
            ]
        }

        httpx_mock.add_response(
            url=httpx.URL(
                "https://api.duffel.com/places/suggestions",
                params={"query": "LAX", "limit": "10", "appid": "test_api_token"},
            ),
            json=mock_response,
        )

        # First call should hit the API
        airports1 = await flights_service.search_airports("LAX")

        # Check that cache was set
        mock_redis.set.assert_called()

        # Set up cache to return data
        mock_redis.get.return_value = json.dumps(
            [airport.model_dump() for airport in airports1]
        )

        # Clear httpx mock to ensure no more requests
        httpx_mock.reset()

        # Second call should use cache
        airports2 = await flights_service.search_airports("LAX")

        # Should get same results from cache
        assert len(airports2) == len(airports1)
        assert airports2[0].iata_code == "LAX"

    @pytest.mark.asyncio
    async def test_request_validation(self, flights_service, httpx_mock):
        """Test request validation for API calls."""
        # Test with invalid passenger data
        with pytest.raises(ValidationError):
            Passenger(
                type="invalid_type",  # Invalid passenger type
                given_name="",  # Empty name
                family_name="Test",
            )

    @pytest.mark.asyncio
    async def test_retry_mechanism(self, flights_service, httpx_mock):
        """Test retry mechanism for failed requests."""
        # First two attempts fail, third succeeds
        httpx_mock.add_response(
            url="https://api.duffel.com/places/suggestions?query=TEST&limit=10&appid=test_api_token",
            status_code=500,
        )
        httpx_mock.add_response(
            url="https://api.duffel.com/places/suggestions?query=TEST&limit=10&appid=test_api_token",
            status_code=500,
        )
        httpx_mock.add_response(
            url="https://api.duffel.com/places/suggestions?query=TEST&limit=10&appid=test_api_token",
            json={"data": []},
        )

        # Should succeed after retries
        airports = await flights_service.search_airports("TEST")
        assert airports == []

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, flights_service, httpx_mock):
        """Test handling of concurrent requests."""
        import asyncio

        # Mock multiple different responses
        cities = ["NYC", "LAX", "CHI", "MIA", "SEA"]
        for city in cities:
            httpx_mock.add_response(
                url=httpx.URL(
                    "https://api.duffel.com/places/suggestions",
                    params={"query": city, "limit": "10", "appid": "test_api_token"},
                ),
                json={
                    "data": [
                        {
                            "id": f"arp_{city.lower()}_us",
                            "type": "airport",
                            "iata_code": city,
                            "name": f"{city} Airport",
                            "city_name": city,
                            "country_name": "United States",
                            "latitude": 0.0,
                            "longitude": 0.0,
                            "time_zone": "America/New_York",
                        }
                    ]
                },
            )

        # Make concurrent requests
        tasks = [flights_service.search_airports(city) for city in cities]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        for i, airports in enumerate(results):
            assert len(airports) == 1
            assert airports[0].iata_code == cities[i]
