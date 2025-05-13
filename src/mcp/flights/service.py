"""
Flight Service for TripSage.

This module provides a high-level service for flight-related operations,
integrating with the FlightsMCPClient, database, and memory components.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from ...db.client import SupabaseDBClient
from ...db.client import get_client as get_db_client
from ...mcp.memory.client import MemoryMCPClient
from ...mcp.memory.client import get_client as get_memory_client
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from .client import FlightsMCPClient, get_client
from .scoring import calculate_flight_value_score, calculate_price_insights

logger = get_module_logger(__name__)


class FlightService:
    """High-level service for flight-related operations in TripSage.

    This service integrates with the ravinahp/flights-mcp server which provides
    flight search functionality through the Duffel API. The server is read-only
    and does not support booking operations.

    The FlightService enhances the basic MCP functionality with additional features:
    1. Dual storage in Supabase and Memory MCP for search results
    2. Price insights and tracking
    3. Best flight recommendations
    """

    def __init__(self, client: Optional[FlightsMCPClient] = None):
        """Initialize the Flight Service.

        Args:
            client: FlightsMCPClient instance. If not provided, uses the default client.
        """
        self.client = client or get_client()
        logger.info("Initialized Flight Service with ravinahp/flights-mcp integration")

        # Log a warning about the read-only nature of the MCP
        logger.info(
            "Note: ravinahp/flights-mcp is read-only - booking operations "
            "are not supported"
        )
        # Initialize clients needed for storage within the service
        self._db_client: Optional[SupabaseDBClient] = None
        self._memory_client: Optional[MemoryMCPClient] = None

    async def _get_db_client(self) -> SupabaseDBClient:
        """Lazy load DB client."""
        if self._db_client is None:
            self._db_client = get_db_client()
        return self._db_client

    async def _get_memory_client(self) -> MemoryMCPClient:
        """Lazy load Memory client."""
        if self._memory_client is None:
            self._memory_client = get_memory_client()
        return self._memory_client

    async def _resolve_airport_code(self, identifier: str) -> str:
        """Resolve city name or IATA code to an IATA code."""
        if len(identifier) == 3 and identifier.isupper():
            # Assume it's already an IATA code
            return identifier

        logger.debug(f"Resolving airport identifier: {identifier}")
        try:
            airports_response = await self.client.get_airports(search_term=identifier)
            if airports_response.airports and len(airports_response.airports) > 0:
                # Return the first match
                resolved_code = airports_response.airports[0].iata_code
                logger.debug(f"Resolved {identifier} to {resolved_code}")
                return resolved_code
            else:
                logger.warning(f"Could not find airport for identifier: {identifier}")
                raise ValueError(f"Could not find airport for {identifier}")
        except Exception as e:
            logger.error(f"Error resolving airport code for {identifier}: {str(e)}")
            raise ValueError(f"Could not resolve airport for {identifier}") from e

    async def _store_results_db(
        self,
        search_id: str,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str],
        results_dict: Dict[str, Any],
        timestamp: str,
    ):
        """Store flight search results in Supabase."""
        try:
            db_client = await self._get_db_client()
            await db_client.store_flight_search_results(
                search_id=search_id,
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                results=results_dict,
                timestamp=timestamp,
            )
            logger.info(f"Stored flight search results in Supabase: {search_id}")
        except Exception as db_error:
            logger.warning(
                f"Error storing flight results in database for {search_id}: "
                f"{str(db_error)}"
            )

    async def _store_results_memory(
        self,
        search_id: str,
        origin_code: str,
        destination_code: str,
        departure_date: str,
        return_date: Optional[str],
        results_dict: Dict[str, Any],
    ):
        """Store flight search results in Memory MCP."""
        try:
            memory_client = await self._get_memory_client()
            num_offers = len(results_dict.get("offers", []))
            best_price_info = "N/A"
            if num_offers > 0 and "offers" in results_dict:
                first_offer = results_dict["offers"][0]
                if isinstance(first_offer, dict):  # Ensure it's a dict after sorting
                    best_price_info = (
                        f"{first_offer.get('total_amount', 'N/A')} "
                        f"{first_offer.get('total_currency', '')}"
                    )

            entities_to_create = [
                {
                    "name": f"Airport:{origin_code}",
                    "entityType": "Airport",
                    "observations": [f"IATA code: {origin_code}"],
                },
                {
                    "name": f"Airport:{destination_code}",
                    "entityType": "Airport",
                    "observations": [f"IATA code: {destination_code}"],
                },
                {
                    "name": f"FlightSearch:{search_id}",
                    "entityType": "FlightSearch",
                    "observations": [
                        f"From {origin_code} to {destination_code}",
                        f"Departure date: {departure_date}",
                        f"Return date: {return_date or 'None (one-way)'}",
                        f"Found {num_offers} offers",
                        f"Lowest price found: {best_price_info}",
                    ],
                },
            ]
            await memory_client.create_entities(entities_to_create)

            relations_to_create = [
                {
                    "from": f"FlightSearch:{search_id}",
                    "relationType": "departs_from",
                    "to": f"Airport:{origin_code}",
                },
                {
                    "from": f"FlightSearch:{search_id}",
                    "relationType": "arrives_at",
                    "to": f"Airport:{destination_code}",
                },
            ]
            await memory_client.create_relations(relations_to_create)

            logger.info(f"Stored flight search results in Memory MCP: {search_id}")
        except Exception as memory_error:
            logger.warning(
                f"Error storing flight results in Memory MCP for {search_id}: "
                f"{str(memory_error)}"
            )

    async def _store_results(
        self, search_response: Dict[str, Any], results_dict: Dict[str, Any]
    ):
        """Store results in both Supabase and Memory MCP."""
        search_id = search_response.get("search_id", "unknown_search")
        origin_code = search_response.get("origin", {}).get("code", "UNK")
        destination_code = search_response.get("destination", {}).get("code", "UNK")
        departure_date = search_response.get("departure_date", "UNK")
        return_date = search_response.get("return_date")
        timestamp = search_response.get("search_timestamp", datetime.now().isoformat())

        # Run storage tasks concurrently
        await asyncio.gather(
            self._store_results_db(
                search_id,
                origin_code,
                destination_code,
                departure_date,
                return_date,
                results_dict,
                timestamp,
            ),
            self._store_results_memory(
                search_id,
                origin_code,
                destination_code,
                departure_date,
                return_date,
                results_dict,
            ),
        )

    async def search_best_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_price: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Search for best flight options, sort by value, and store results.

        Args:
            origin: Origin airport IATA code or city name
            destination: Destination airport IATA code or city name
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)
            adults: Number of adult passengers
            max_price: Maximum price in USD

        Returns:
            Dictionary containing best flight options and metadata
        """
        search_timestamp = datetime.now().isoformat()
        origin_input, destination_input = origin, destination
        origin_code, destination_code = None, None
        search_id_prefix = f"{origin_input}-{destination_input}-{departure_date}"
        search_id = f"{search_id_prefix}-{search_timestamp}"  # More unique ID

        try:
            # 1. Resolve Airport Codes
            origin_code = await self._resolve_airport_code(origin_input)
            destination_code = await self._resolve_airport_code(destination_input)
            # Update search ID with resolved codes if successful
            search_id_prefix = f"{origin_code}-{destination_code}-{departure_date}"
            search_id = f"{search_id_prefix}-{search_timestamp}"

            # 2. Search for flights via MCP Client
            logger.info(
                f"Searching flights: {origin_code} -> {destination_code} "
                f"on {departure_date}"
            )
            results = await self.client.search_flights(
                origin=origin_code,
                destination=destination_code,
                departure_date=departure_date,
                return_date=return_date,
                adults=adults,
                max_price=max_price,
                skip_cache=False,  # Allow caching for searches
            )

            results_dict = results.model_dump(exclude_none=True)
            offers_list = results_dict.get("offers", [])

            # 3. Sort results by value score if offers exist
            if offers_list:
                logger.info(f"Found {len(offers_list)} offers. Calculating scores...")
                # Calculate scores and sort
                scored_offers = []
                for offer_data in offers_list:
                    # Check if offer_data is already a dict, if not
                    # (e.g., Offer model), dump it
                    offer_dict = (
                        offer_data
                        if isinstance(offer_data, dict)
                        else offer_data.model_dump(exclude_none=True)
                    )
                    offer_dict["_value_score"] = calculate_flight_value_score(
                        offer_dict
                    )
                    scored_offers.append(offer_dict)

                scored_offers.sort(key=lambda x: x.get("_value_score", float("inf")))

                # Remove internal score before storing/returning
                for offer_data in scored_offers:
                    if "_value_score" in offer_data:
                        del offer_data["_value_score"]

                results_dict["offers"] = (
                    scored_offers  # Update results with sorted list
                )
                logger.info("Offers sorted by value score.")
            else:
                logger.info("No flight offers found.")
                # Ensure results_dict has an empty 'offers' list if none found
                results_dict["offers"] = []

            # 4. Format response
            search_response = {
                "origin": {"code": origin_code, "input": origin_input},
                "destination": {"code": destination_code, "input": destination_input},
                "departure_date": departure_date,
                "return_date": return_date,
                "adults": adults,
                "max_price": max_price,
                "search_id": search_id,
                "search_timestamp": search_timestamp,
                "results": results_dict,  # Include the full results dict
            }

            # 5. Store results (asynchronously)
            await self._store_results(search_response, results_dict)

            return search_response

        except ValueError as ve:  # Catch specific airport resolution errors
            logger.error(f"Airport resolution failed: {str(ve)}")
            # Don't store errors related to bad input (invalid airport)
            return {
                "error": f"Failed to resolve airport: {str(ve)}",
                "origin_input": origin_input,
                "destination_input": destination_input,
                "search_id": search_id,
                "search_timestamp": search_timestamp,
            }
        except MCPError as mcp_e:
            logger.error(
                f"MCP Error during flight search for {search_id_prefix}: {mcp_e}"
            )
            error_dict = {
                "error": f"MCP Error: {mcp_e.message}",
                "details": mcp_e.to_dict(),  # Include MCPError details
            }
            error_response = {
                "origin": (
                    {"code": origin_code, "input": origin_input}
                    if origin_code
                    else {"input": origin_input}
                ),
                "destination": (
                    {"code": destination_code, "input": destination_input}
                    if destination_code
                    else {"input": destination_input}
                ),
                "departure_date": departure_date,
                "return_date": return_date,
                "search_id": search_id,
                "search_timestamp": search_timestamp,
                "results": error_dict,  # Store error details in results
            }
            # Store MCP errors for analysis
            await self._store_results(error_response, error_dict)
            return error_response

        except Exception as e:
            logger.exception(
                f"Unexpected error during flight search for {search_id_prefix}: "
                f"{str(e)}"
            )
            error_dict = {"error": f"Unexpected error searching flights: {str(e)}"}
            error_response = {
                "origin": (
                    {"code": origin_code, "input": origin_input}
                    if origin_code
                    else {"input": origin_input}
                ),
                "destination": (
                    {"code": destination_code, "input": destination_input}
                    if destination_code
                    else {"input": destination_input}
                ),
                "departure_date": departure_date,
                "return_date": return_date,
                "search_id": search_id,
                "search_timestamp": search_timestamp,
                "results": error_dict,  # Store error details in results
            }
            # Store unexpected errors for analysis
            await self._store_results(error_response, error_dict)
            return error_response

    async def get_price_insights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        return_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get pricing insights for a route, including trends and recommendations.

        Args:
            origin: Origin airport IATA code
            destination: Destination airport IATA code
            departure_date: Departure date (YYYY-MM-DD)
            return_date: Return date for round trips (YYYY-MM-DD)

        Returns:
            Dictionary with pricing insights and recommendations
        """
        try:
            # Get price history
            price_history_response = await self.client.get_flight_prices(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
            )
            price_history_data = price_history_response.model_dump(exclude_none=True)

            # Get current prices (use search_best_flights to leverage its logic)
            current_search = await self.search_best_flights(
                origin=origin,
                destination=destination,
                departure_date=departure_date,
                return_date=return_date,
                adults=1,  # Use 1 adult for price comparison baseline
            )

            # Extract lowest current price from the search results
            lowest_current_price = None
            current_currency = None
            if (
                current_search
                and "results" in current_search
                and isinstance(current_search["results"], dict)
                and "offers" in current_search["results"]
                and current_search["results"]["offers"]
            ):
                first_offer_data = current_search["results"]["offers"][0]
                if isinstance(first_offer_data, dict):
                    lowest_current_price = first_offer_data.get("total_amount")
                    current_currency = first_offer_data.get("total_currency")
                # No need to check for Offer model instance if offers are
                # always dicts after sorting

            # Prepare base insights structure
            response_insights = {
                "origin": origin,
                "destination": destination,
                "departure_date": departure_date,
                "return_date": return_date,
                "current_lowest_price": lowest_current_price,
                "currency": current_currency,
                # Initialize keys that calculate_price_insights will fill
                "historical": {},
                "analysis": {},
                "recommendation": "unavailable",
            }

            # Calculate insights using the new function
            calculated_insights = calculate_price_insights(
                price_history_data, lowest_current_price
            )

            # Merge calculated insights into the response structure
            response_insights.update(
                calculated_insights
            )  # Merges historical, analysis, recommendation

            # Optionally include raw history data
            # response_insights["price_history_raw"] = price_history_data

            return response_insights

        except MCPError as mcp_e:
            logger.error(
                f"MCP Error getting price insights for {origin}-{destination}: {mcp_e}"
            )
            return {
                "error": f"MCP Error getting price insights: {mcp_e.message}",
                "origin": origin,
                "destination": destination,
                "details": mcp_e.to_dict(),
            }

        except Exception as e:
            logger.exception(
                f"Unexpected error getting price insights for {origin}-{destination}: "
                f"{str(e)}"
            )
            return {
                "error": f"Unexpected error getting price insights: {str(e)}",
                "origin": origin,
                "destination": destination,
            }


def get_service() -> FlightService:
    """Get a Flight Service instance.

    Returns:
        FlightService instance
    """
    return FlightService(get_client())
