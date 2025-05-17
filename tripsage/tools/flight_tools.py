"""
Flight search tools for TripSage agents.

This module provides function tools for flight search and booking using the
Duffel Flights MCP client via the MCPManager abstraction layer.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents import function_tool

from tripsage.mcp_abstraction.exceptions import TripSageMCPError
from tripsage.mcp_abstraction.manager import mcp_manager
from tripsage.tools.schemas.flights import (
    AirportSearchParams,
    AirportSearchResponse,
    CabinClass,
    FlightPriceParams,
    FlightPriceResponse,
    FlightSearchParams,
    FlightSearchResponse,
    MultiCitySearchParams,
    OfferDetailsParams,
    OfferDetailsResponse,
    PriceTrackingParams,
    PriceTrackingResponse,
)
from tripsage.utils.error_handling import with_error_handling
from tripsage.utils.logging import get_logger

# Set up logger
logger = get_logger(__name__)


@function_tool
@with_error_handling
async def search_flights_tool(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: str = "economy",
    max_stops: Optional[int] = None,
    max_price: Optional[float] = None,
    preferred_airlines: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Search for flights.

    Args:
        origin: Origin airport IATA code (3 letters)
        destination: Destination airport IATA code (3 letters)
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format for round trips
        adults: Number of adult passengers (1-9)
        children: Number of child passengers (0-9)
        infants: Number of infant passengers (0-4)
        cabin_class: Cabin class (economy, premium_economy, business, first)
        max_stops: Maximum number of stops
        max_price: Maximum price in USD
        preferred_airlines: List of preferred airline codes

    Returns:
        Flight search results
    """
    try:
        logger.info(
            f"Searching flights from {origin} to {destination} on {departure_date}"
        )

        # Parse cabin class from string to enum
        cabin_class_enum = CabinClass.ECONOMY
        try:
            cabin_class_enum = CabinClass(cabin_class.lower())
        except ValueError:
            logger.warning(
                f"Invalid cabin class: {cabin_class}. Using economy instead."
            )

        # Prepare search params
        search_params = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": adults,
            "cabin_class": cabin_class_enum,
        }

        # Add optional parameters
        if return_date:
            search_params["return_date"] = return_date
        if children:
            search_params["children"] = children
        if infants:
            search_params["infants"] = infants
        if max_stops is not None:
            search_params["max_stops"] = max_stops
        if max_price is not None:
            search_params["max_price"] = max_price
        if preferred_airlines:
            search_params["preferred_airlines"] = preferred_airlines

        # Create validated model
        validated_params = FlightSearchParams(**search_params)

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="duffel_flights",
            method_name="search_flights",
            params=validated_params.model_dump(by_alias=True),
        )

        # Convert the result to the expected response model
        result = FlightSearchResponse.model_validate(result)

        # Apply post-search filtering
        filtered_offers = result.offers

        # Filter by max_price if provided
        if max_price is not None:
            filtered_offers = [
                offer for offer in filtered_offers if offer.total_amount <= max_price
            ]

        # Filter by max_stops if provided
        if max_stops is not None:
            filtered_offers = [
                offer
                for offer in filtered_offers
                if all(
                    len(slice.get("segments", [])) - 1 <= max_stops
                    for slice in offer.slices
                )
            ]

        # Filter by preferred_airlines if provided
        if preferred_airlines and len(preferred_airlines) > 0:
            # Put preferred airlines first, then others
            preferred = [
                offer
                for offer in filtered_offers
                if any(
                    segment.get("operating_carrier_code") in preferred_airlines
                    for slice in offer.slices
                    for segment in slice.get("segments", [])
                )
            ]

            non_preferred = [
                offer
                for offer in filtered_offers
                if not any(
                    segment.get("operating_carrier_code") in preferred_airlines
                    for slice in offer.slices
                    for segment in slice.get("segments", [])
                )
            ]

            filtered_offers = preferred + non_preferred

        # Format results for agent consumption
        formatted_offers = []
        for offer in filtered_offers[:20]:  # Limit to 20 offers for readability
            formatted_offer = {
                "id": offer.id,
                "price": {
                    "total": offer.total_amount,
                    "currency": offer.total_currency,
                    "base": offer.base_amount,
                    "taxes": offer.tax_amount,
                },
                "slices": [],
            }

            # Format each slice (outbound and return)
            for slice_idx, slice_data in enumerate(offer.slices):
                slice_info = {
                    "type": "outbound" if slice_idx == 0 else "return",
                    "origin": slice_data.get("origin", {}).get("iata_code", ""),
                    "destination": slice_data.get("destination", {}).get(
                        "iata_code", ""
                    ),
                    "departure": slice_data.get("departure", {}).get("datetime", ""),
                    "arrival": slice_data.get("arrival", {}).get("datetime", ""),
                    "duration_minutes": slice_data.get("duration_minutes", 0),
                    "stops": len(slice_data.get("segments", [])) - 1,
                    "segments": [],
                }

                # Format each segment (flight leg)
                for segment in slice_data.get("segments", []):
                    segment_info = {
                        "origin": segment.get("origin", {}).get("iata_code", ""),
                        "destination": segment.get("destination", {}).get(
                            "iata_code", ""
                        ),
                        "departure": segment.get("departure", {}).get("datetime", ""),
                        "arrival": segment.get("arrival", {}).get("datetime", ""),
                        "flight_number": segment.get("flight_number", ""),
                        "carrier": segment.get("marketing_carrier", {}).get("name", ""),
                        "carrier_code": segment.get("marketing_carrier_code", ""),
                        "aircraft": segment.get("aircraft", {}).get("name", ""),
                        "cabin_class": segment.get("cabin_class", ""),
                    }
                    slice_info["segments"].append(segment_info)

                formatted_offer["slices"].append(slice_info)

            formatted_offers.append(formatted_offer)

        # Return search results
        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "offers": formatted_offers,
            "offer_count": len(filtered_offers),
            "cheapest_price": (
                min([offer.total_amount for offer in filtered_offers])
                if filtered_offers
                else None
            ),
            "currency": result.currency,
        }

    except TripSageMCPError as e:
        logger.error(f"MCP error searching flights: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error searching flights: {str(e)}")
        raise


@function_tool
@with_error_handling
async def search_airports_tool(
    search_term: Optional[str] = None,
    code: Optional[str] = None,
) -> Dict[str, Any]:
    """Search for airports by name or code.

    Args:
        search_term: Airport name, city, or part of name
        code: IATA airport code (3 letters)

    Returns:
        List of matching airports
    """
    try:
        if not search_term and not code:
            return {"error": "Either search_term or code must be provided"}

        # Create validated model
        validated_params = AirportSearchParams(
            search_term=search_term,
            code=code.upper() if code else None,
        )

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="duffel_flights",
            method_name="get_airports",
            params=validated_params.model_dump(by_alias=True),
        )

        # Convert the result to the expected response model
        result = AirportSearchResponse.model_validate(result)

        # Format results for agent consumption
        formatted_airports = []
        for airport in result.airports:
            formatted_airport = {
                "code": airport.iata_code,
                "name": airport.name,
                "city": airport.city,
                "country": airport.country,
                "location": (
                    {
                        "latitude": airport.latitude,
                        "longitude": airport.longitude,
                    }
                    if airport.latitude and airport.longitude
                    else None
                ),
                "timezone": airport.timezone,
            }
            formatted_airports.append(formatted_airport)

        return {
            "airports": formatted_airports,
            "count": len(formatted_airports),
            "query": search_term or code,
        }

    except TripSageMCPError as e:
        logger.error(f"MCP error searching airports: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error searching airports: {str(e)}")
        raise


@function_tool
@with_error_handling
async def get_flight_prices_tool(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Get flight price history.

    Args:
        origin: Origin airport IATA code (3 letters)
        destination: Destination airport IATA code (3 letters)
        departure_date: Departure date in YYYY-MM-DD format
        return_date: Return date in YYYY-MM-DD format for round trips

    Returns:
        Flight price history and trend
    """
    try:
        logger.info(
            f"Getting price history for {origin} to {destination} on {departure_date}"
        )

        # Create validated model
        validated_params = FlightPriceParams(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
        )

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="duffel_flights",
            method_name="get_flight_prices",
            params=validated_params.model_dump(by_alias=True),
        )

        # Convert the result to the expected response model
        result = FlightPriceResponse.model_validate(result)

        # Format price history data
        price_history = {
            "origin": result.origin,
            "destination": result.destination,
            "departure_date": result.departure_date,
            "return_date": result.return_date,
            "current_price": result.current_price,
            "currency": result.currency,
            "prices": result.prices,
            "dates": result.dates,
            "trend": result.trend,
            "average_price": (
                sum(result.prices) / len(result.prices) if result.prices else None
            ),
            "min_price": min(result.prices) if result.prices else None,
            "max_price": max(result.prices) if result.prices else None,
        }

        # Add recommendation based on current price
        if result.current_price and result.prices:
            avg_price = sum(result.prices) / len(result.prices)
            min_price = min(result.prices)

            if result.current_price <= min_price * 1.05:
                price_history["recommendation"] = "book_now"
            elif result.current_price <= avg_price * 0.8:
                price_history["recommendation"] = "great_deal"
            elif result.current_price <= avg_price * 0.9:
                price_history["recommendation"] = "good_deal"
            elif result.current_price <= avg_price * 1.1:
                price_history["recommendation"] = "fair_price"
            else:
                price_history["recommendation"] = "monitor"

        return price_history

    except TripSageMCPError as e:
        logger.error(f"MCP error getting flight prices: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error getting flight prices: {str(e)}")
        raise


@function_tool
@with_error_handling
async def get_offer_details_tool(
    offer_id: str,
) -> Dict[str, Any]:
    """Get details of a specific flight offer.

    Args:
        offer_id: Flight offer ID

    Returns:
        Flight offer details
    """
    try:
        logger.info(f"Getting details for offer: {offer_id}")

        # Create validated model
        validated_params = OfferDetailsParams(offer_id=offer_id)

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="duffel_flights",
            method_name="get_offer_details",
            params=validated_params.model_dump(by_alias=True),
        )

        # Convert the result to the expected response model
        result = OfferDetailsResponse.model_validate(result)

        # Format offer details
        offer_details = {
            "offer_id": result.offer_id,
            "price": {
                "total": result.total_amount,
                "currency": result.currency,
            },
            "slices": result.slices,
            "passengers": result.passengers,
            "fare_details": result.fare_details,
        }

        return offer_details

    except TripSageMCPError as e:
        logger.error(f"MCP error getting offer details: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error getting offer details: {str(e)}")
        raise


@function_tool
@with_error_handling
async def track_flight_prices_tool(
    origin: str,
    destination: str,
    departure_date: str,
    email: str,
    return_date: Optional[str] = None,
    frequency: str = "daily",
    threshold_percentage: Optional[float] = None,
) -> Dict[str, Any]:
    """Track flight prices and receive alerts.

    Args:
        origin: Origin airport IATA code (3 letters)
        destination: Destination airport IATA code (3 letters)
        departure_date: Departure date in YYYY-MM-DD format
        email: Email address to receive alerts
        return_date: Return date in YYYY-MM-DD format for round trips
        frequency: Alert frequency (hourly, daily, weekly)
        threshold_percentage: Alert when price drops by this percentage

    Returns:
        Price tracking confirmation
    """
    try:
        logger.info(
            f"Setting up price tracking for {origin} to {destination} "
            f"on {departure_date}"
        )

        # Create validated model
        validated_params = PriceTrackingParams(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            return_date=return_date,
            email=email,
            frequency=frequency,
            threshold_percentage=threshold_percentage,
        )

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="duffel_flights",
            method_name="track_flight_prices",
            params=validated_params.model_dump(by_alias=True),
        )

        # Convert the result to the expected response model
        result = PriceTrackingResponse.model_validate(result)

        # Format tracking confirmation
        tracking_info = {
            "tracking_id": result.tracking_id,
            "route": f"{result.origin} to {result.destination}",
            "departure_date": result.departure_date,
            "return_date": result.return_date,
            "email": result.email,
            "frequency": result.frequency,
            "current_price": result.current_price,
            "currency": result.currency,
            "threshold_price": result.threshold_price,
            "message": (
                f"Price alerts will be sent to {result.email} {result.frequency}"
            ),
        }

        return tracking_info

    except TripSageMCPError as e:
        logger.error(f"MCP error setting up price tracking: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error setting up price tracking: {str(e)}")
        raise


@function_tool
@with_error_handling
async def search_flexible_dates_tool(
    origin: str,
    destination: str,
    date_from: str,
    date_to: str,
    trip_length: Optional[int] = None,
    adults: int = 1,
    cabin_class: str = "economy",
) -> Dict[str, Any]:
    """Search for flights with flexible dates to find the best deals.

    Args:
        origin: Origin airport IATA code (3 letters)
        destination: Destination airport IATA code (3 letters)
        date_from: Start date for flexible search (YYYY-MM-DD)
        date_to: End date for flexible search (YYYY-MM-DD)
        trip_length: Length of trip in days (for round trips)
        adults: Number of adult passengers
        cabin_class: Cabin class

    Returns:
        Best flight options across the date range
    """
    try:
        logger.info(
            f"Searching flexible dates from {origin} to {destination} "
            f"({date_from} to {date_to})"
        )

        # Validate dates
        try:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d")
        except ValueError:
            return {"error": "Dates must be in YYYY-MM-DD format"}

        # Limit search range to 30 days to avoid too many API calls
        if (date_to_obj - date_from_obj).days > 30:
            date_to_obj = date_from_obj + timedelta(days=30)
            date_to = date_to_obj.strftime("%Y-%m-%d")

        # Generate dates to search (every 3 days to reduce API calls)
        dates_to_search = []
        current_date = date_from_obj
        while current_date <= date_to_obj:
            dates_to_search.append(current_date.strftime("%Y-%m-%d"))
            current_date += timedelta(days=3)

        # Parse cabin class from string to enum
        cabin_class_enum = CabinClass.ECONOMY
        try:
            cabin_class_enum = CabinClass(cabin_class.lower())
        except ValueError:
            logger.warning(
                f"Invalid cabin class: {cabin_class}. Using economy instead."
            )

        # Search flights for each date combination
        results = []
        for dep_date in dates_to_search:
            search_params = {
                "origin": origin,
                "destination": destination,
                "departure_date": dep_date,
                "adults": adults,
                "cabin_class": cabin_class_enum,
            }

            # Add return date if trip length specified
            if trip_length:
                ret_date = (
                    datetime.strptime(dep_date, "%Y-%m-%d")
                    + timedelta(days=trip_length)
                ).strftime("%Y-%m-%d")
                search_params["return_date"] = ret_date

            # Search flights
            try:
                # Create validated model
                validated_params = FlightSearchParams(**search_params)

                # Call the MCP via MCPManager
                result = await mcp_manager.invoke(
                    mcp_name="duffel_flights",
                    method_name="search_flights",
                    params=validated_params.model_dump(by_alias=True),
                )

                # Convert the result to the expected response model
                result = FlightSearchResponse.model_validate(result)

                # Extract best price for this date
                if result.offers:
                    best_price = min(offer.total_amount for offer in result.offers)

                    results.append(
                        {
                            "departure_date": dep_date,
                            "return_date": search_params.get("return_date"),
                            "best_price": best_price,
                            "currency": result.currency,
                            "offer_count": len(result.offers),
                        }
                    )
            except Exception as e:
                logger.warning(f"Error searching flights for {dep_date}: {str(e)}")

        # Sort by price
        results.sort(key=lambda x: x.get("best_price", float("inf")))

        # Generate recommendation
        recommendation = None
        avg_price = 0
        savings_percent = 0

        if results:
            cheapest = results[0]
            # Calculate average price
            avg_price = sum(r.get("best_price", 0) for r in results) / len(results)
            # Calculate savings
            savings = avg_price - cheapest.get("best_price", 0)
            savings_percent = (savings / avg_price) * 100 if avg_price > 0 else 0

            if savings_percent >= 30:
                recommendation = "significant_savings"
            elif savings_percent >= 15:
                recommendation = "good_savings"
            else:
                recommendation = "minor_savings"

        return {
            "origin": origin,
            "destination": destination,
            "date_range": {"from": date_from, "to": date_to},
            "trip_length": trip_length,
            "best_date": results[0] if results else None,
            "all_dates": results,
            "total_options": len(results),
            "recommendation": recommendation,
            "savings": (
                {
                    "amount": round(avg_price - results[0].get("best_price", 0), 2),
                    "percent": round(savings_percent, 1),
                }
                if results
                else None
            ),
        }

    except TripSageMCPError as e:
        logger.error(f"MCP error searching flexible dates: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error searching flexible dates: {str(e)}")
        raise


@function_tool
@with_error_handling
async def search_multi_city_flights_tool(
    segments: List[Dict[str, Any]],
    adults: int = 1,
    children: int = 0,
    infants: int = 0,
    cabin_class: str = "economy",
) -> Dict[str, Any]:
    """Search for multi-city flights.

    Args:
        segments: List of flight segments
            (each with origin, destination, departure_date)
        adults: Number of adult passengers
        children: Number of child passengers
        infants: Number of infant passengers
        cabin_class: Cabin class

    Returns:
        Multi-city flight search results
    """
    try:
        logger.info(f"Searching multi-city flights with {len(segments)} segments")

        # Validate segments
        if len(segments) < 2:
            return {"error": "At least two segments are required for multi-city search"}

        # Parse cabin class from string to enum
        cabin_class_enum = CabinClass.ECONOMY
        try:
            cabin_class_enum = CabinClass(cabin_class.lower())
        except ValueError:
            logger.warning(
                f"Invalid cabin class: {cabin_class}. Using economy instead."
            )

        # Create validated model
        validated_params = MultiCitySearchParams(
            segments=segments,
            adults=adults,
            children=children,
            infants=infants,
            cabin_class=cabin_class_enum,
        )

        # Call the MCP via MCPManager
        result = await mcp_manager.invoke(
            mcp_name="duffel_flights",
            method_name="search_multi_city",
            params=validated_params.model_dump(by_alias=True),
        )

        # Convert the result to the expected response model
        result = FlightSearchResponse.model_validate(result)

        # Format results for agent consumption (similar to search_flights_tool)
        formatted_offers = []
        for offer in result.offers[:10]:  # Limit to 10 offers for readability
            formatted_offer = {
                "id": offer.id,
                "price": {
                    "total": offer.total_amount,
                    "currency": offer.total_currency,
                    "base": offer.base_amount,
                    "taxes": offer.tax_amount,
                },
                "slices": [],
            }

            # Format each slice (segment)
            for slice_idx, slice_data in enumerate(offer.slices):
                slice_info = {
                    "segment": slice_idx + 1,
                    "origin": slice_data.get("origin", {}).get("iata_code", ""),
                    "destination": slice_data.get("destination", {}).get(
                        "iata_code", ""
                    ),
                    "departure": slice_data.get("departure", {}).get("datetime", ""),
                    "arrival": slice_data.get("arrival", {}).get("datetime", ""),
                    "duration_minutes": slice_data.get("duration_minutes", 0),
                    "stops": len(slice_data.get("segments", [])) - 1,
                    "segments": [],
                }

                # Format each segment (flight leg)
                for segment in slice_data.get("segments", []):
                    segment_info = {
                        "origin": segment.get("origin", {}).get("iata_code", ""),
                        "destination": segment.get("destination", {}).get(
                            "iata_code", ""
                        ),
                        "departure": segment.get("departure", {}).get("datetime", ""),
                        "arrival": segment.get("arrival", {}).get("datetime", ""),
                        "flight_number": segment.get("flight_number", ""),
                        "carrier": segment.get("marketing_carrier", {}).get("name", ""),
                        "carrier_code": segment.get("marketing_carrier_code", ""),
                        "aircraft": segment.get("aircraft", {}).get("name", ""),
                        "cabin_class": segment.get("cabin_class", ""),
                    }
                    slice_info["segments"].append(segment_info)

                formatted_offer["slices"].append(slice_info)

            formatted_offers.append(formatted_offer)

        # Return search results
        return {
            "segments": [
                {
                    "origin": segment.origin,
                    "destination": segment.destination,
                    "departure_date": segment.departure_date,
                }
                for segment in validated_params.segments
            ],
            "offers": formatted_offers,
            "offer_count": len(result.offers),
            "cheapest_price": (
                min([offer.total_amount for offer in result.offers])
                if result.offers
                else None
            ),
            "currency": result.currency,
        }

    except TripSageMCPError as e:
        logger.error(f"MCP error searching multi-city flights: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error searching multi-city flights: {str(e)}")
        raise
