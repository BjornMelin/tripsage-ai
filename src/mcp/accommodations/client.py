"""
Airbnb MCP client for the TripSage travel planning system.

This module provides a client for the Airbnb MCP server, which allows searching
for accommodations and retrieving detailed listing information.
"""

from datetime import date
from typing import List, Optional, TypeVar, Union

from pydantic import ValidationError

from ...db.client import get_client as get_db_client
from ...db.repositories.accommodation import AccommodationRepository
from ...utils.config import get_config
from ...utils.error_handling import MCPError
from ...utils.logging import get_module_logger
from ..base_mcp_client import BaseMCPClient
from ..memory.client import memory_client
from .models import (
    AirbnbListingDetails,
    AirbnbSearchParams,
    AirbnbSearchResult,
)

logger = get_module_logger(__name__)
config = get_config()

# Define type variables for generic parameters and responses
P = TypeVar("P", bound=AirbnbSearchParams)
R = TypeVar("R", bound=AirbnbSearchResult)


class AirbnbMCPClient(BaseMCPClient[P, R]):
    """Client for the Airbnb MCP server."""

    def __init__(
        self,
        endpoint: str = "http://localhost:3000",
        server_type: str = "openbnb/mcp-server-airbnb",
        timeout: float = 60.0,
        use_cache: bool = True,
        cache_ttl: int = 3600,  # 1 hour default
    ):
        """Initialize the Airbnb MCP client.

        Args:
            endpoint: MCP server endpoint URL
            server_type: Type of server implementation
                (e.g., "openbnb/mcp-server-airbnb")
            timeout: Request timeout in seconds
            use_cache: Whether to use caching
            cache_ttl: Cache TTL in seconds
        """
        super().__init__(
            endpoint=endpoint,
            api_key=None,  # OpenBnB Airbnb MCP doesn't use API keys
            timeout=timeout,
            use_cache=use_cache,
            cache_ttl=cache_ttl,
        )
        self.server_name = "OpenBnB Airbnb MCP"
        self.server_type = server_type
        logger.debug(
            "Initialized %s client with endpoint: %s", self.server_name, endpoint
        )

    async def search_accommodations(
        self,
        location: str,
        place_id: Optional[str] = None,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
        adults: Optional[int] = None,
        children: Optional[int] = None,
        infants: Optional[int] = None,
        pets: Optional[int] = None,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        min_beds: Optional[int] = None,
        min_bedrooms: Optional[int] = None,
        min_bathrooms: Optional[int] = None,
        property_type: Optional[str] = None,
        amenities: Optional[List[str]] = None,
        room_type: Optional[str] = None,
        superhost: Optional[bool] = None,
        cursor: Optional[str] = None,
        ignore_robots_txt: bool = False,
        skip_cache: bool = False,
        store_results: bool = True,
    ) -> AirbnbSearchResult:
        """Search for Airbnb listings based on location and filters.

        Args:
            location: Location to search for
            place_id: Google Maps place ID
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of adults
            children: Number of children
            infants: Number of infants
            pets: Number of pets
            min_price: Minimum price
            max_price: Maximum price
            min_beds: Minimum number of beds
            min_bedrooms: Minimum number of bedrooms
            min_bathrooms: Minimum number of bathrooms
            property_type: Type of property
            amenities: List of required amenities
            room_type: Room type
            superhost: Filter for superhost listings only
            cursor: Pagination cursor
            ignore_robots_txt: Whether to ignore robots.txt
            skip_cache: Whether to skip the cache
            store_results: Whether to store results in database and memory

        Returns:
            Search results containing listings with details

        Raises:
            MCPError: If the search fails
        """
        try:
            # Validate and prepare parameters using Pydantic model
            search_params = AirbnbSearchParams(
                location=location,
                place_id=place_id,
                checkin=checkin,
                checkout=checkout,
                adults=adults if adults is not None else 1,
                children=children,
                infants=infants,
                pets=pets,
                min_price=min_price,
                max_price=max_price,
                min_beds=min_beds,
                min_bedrooms=min_bedrooms,
                min_bathrooms=min_bathrooms,
                property_type=property_type,
                amenities=amenities,
                room_type=room_type,
                superhost=superhost,
                cursor=cursor,
                ignore_robots_txt=ignore_robots_txt,
            )

            # Convert to MCP parameters
            params = search_params.model_dump(exclude_none=True)

            # Map Pydantic parameter names to the ones expected by the MCP server
            if "min_price" in params:
                params["minPrice"] = params.pop("min_price")
            if "max_price" in params:
                params["maxPrice"] = params.pop("max_price")
            if "place_id" in params:
                params["placeId"] = params.pop("place_id")
            if "ignore_robots_txt" in params:
                params["ignoreRobotsText"] = params.pop("ignore_robots_txt")
            if "min_beds" in params:
                params["minBeds"] = params.pop("min_beds")
            if "min_bedrooms" in params:
                params["minBedrooms"] = params.pop("min_bedrooms")
            if "min_bathrooms" in params:
                params["minBathrooms"] = params.pop("min_bathrooms")
            if "property_type" in params:
                params["propertyType"] = params.pop("property_type")
            if "room_type" in params:
                params["roomType"] = params.pop("room_type")

            logger.info(
                "Searching Airbnb accommodations in %s with filters: %s",
                location,
                {k: v for k, v in params.items() if k != "location"},
            )

            # Call the airbnb_search tool
            result = await self.call_tool("airbnb_search", params, skip_cache)

            # Parse result using Pydantic model
            search_result = AirbnbSearchResult.model_validate(
                {
                    "location": location,
                    "count": len(result.get("listings", [])),
                    "listings": result.get("listings", []),
                    "next_cursor": result.get("next_cursor"),
                    "search_params": params,
                }
            )

            logger.info(
                "Found %s Airbnb listings in %s",
                search_result.count,
                location,
            )

            # Store results in database and memory if requested
            if store_results and search_result.count > 0:
                await self._store_search_results(search_result, checkin, checkout)

            return search_result
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=f"Invalid parameters for accommodation search: {str(e)}",
                server=self.server_name,
                tool="airbnb_search",
                params={"location": location},
            ) from e
        except Exception as e:
            error_msg = (
                f"{self.server_name} ({self.server_type}) accommodation search failed: "
                f"{str(e)}"
            )
            logger.error(error_msg)
            return AirbnbSearchResult.model_validate(
                {
                    "location": location,
                    "count": 0,
                    "listings": [],
                    "search_params": params if "params" in locals() else {},
                    "error": error_msg,
                }
            )

    async def get_listing_details(
        self,
        listing_id: str,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
        adults: Optional[int] = None,
        children: Optional[int] = None,
        infants: Optional[int] = None,
        pets: Optional[int] = None,
        ignore_robots_txt: bool = False,
        skip_cache: bool = False,
        store_results: bool = True,
    ) -> AirbnbListingDetails:
        """Get detailed information about a specific Airbnb listing.

        Args:
            listing_id: Airbnb listing ID
            checkin: Check-in date (YYYY-MM-DD)
            checkout: Check-out date (YYYY-MM-DD)
            adults: Number of adults
            children: Number of children
            infants: Number of infants
            pets: Number of pets
            ignore_robots_txt: Whether to ignore robots.txt
            skip_cache: Whether to skip the cache
            store_results: Whether to store results in database and memory

        Returns:
            Detailed listing information

        Raises:
            MCPError: If the request fails
        """
        # Convert date objects to strings if needed
        if isinstance(checkin, date):
            checkin = checkin.isoformat()
        if isinstance(checkout, date):
            checkout = checkout.isoformat()

        # Prepare parameters
        params = {
            "id": listing_id,
        }

        # Add optional parameters if provided
        if checkin:
            params["checkin"] = checkin
        if checkout:
            params["checkout"] = checkout
        if adults is not None:
            params["adults"] = adults
        if children is not None:
            params["children"] = children
        if infants is not None:
            params["infants"] = infants
        if pets is not None:
            params["pets"] = pets
        if ignore_robots_txt:
            params["ignoreRobotsText"] = ignore_robots_txt

        try:
            logger.info("Getting details for Airbnb listing %s", listing_id)

            # Call the airbnb_listing_details tool
            result = await self.call_tool("airbnb_listing_details", params, skip_cache)

            # Parse result using Pydantic model
            listing_details = AirbnbListingDetails.model_validate(result)

            logger.info(
                "Successfully retrieved details for Airbnb listing %s: %s",
                listing_id,
                listing_details.name,
            )

            # Store detailed listing in memory if requested
            if store_results:
                await self._store_listing_details(listing_details, checkin, checkout)

            return listing_details
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            raise MCPError(
                message=(
                    f"Invalid response from {self.server_name} listing details: "
                    f"{str(e)}"
                ),
                server=self.server_name,
                tool="airbnb_listing_details",
                params=params,
            ) from e
        except Exception as e:
            error_msg = (
                f"Failed to get {self.server_name} ({self.server_type}) "
                f"listing details: {str(e)}"
            )
            logger.error(error_msg)
            raise MCPError(
                message=error_msg,
                server=self.endpoint,
                tool="airbnb_listing_details",
                params=params,
            ) from e

    async def _store_search_results(
        self,
        search_result: AirbnbSearchResult,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
    ) -> None:
        """Store search results in database and knowledge graph.

        Args:
            search_result: Airbnb search results
            checkin: Check-in date
            checkout: Check-out date
        """
        try:
            # Store in Supabase
            db_client = get_db_client()
            accommodation_repo: AccommodationRepository = db_client.accommodations

            # Store in memory
            memory_entities = []
            location = search_result.location

            for listing in search_result.listings[:5]:  # Limit to top 5 for memory
                # Create or update in database
                accommodation_data = {
                    "external_id": listing.id,
                    "name": listing.name,
                    "type": "airbnb",
                    "location": listing.location_info,
                    "price": listing.price_total,
                    "status": "available",
                    "metadata": listing.model_dump(
                        exclude={"id", "name", "location_info"}
                    ),
                }

                if checkin:
                    accommodation_data["check_in_date"] = (
                        checkin.isoformat() if isinstance(checkin, date) else checkin
                    )
                if checkout:
                    accommodation_data["check_out_date"] = (
                        checkout.isoformat() if isinstance(checkout, date) else checkout
                    )

                # Store in Supabase asynchronously
                try:
                    await accommodation_repo.create_or_update(accommodation_data)
                except Exception as e:
                    logger.warning(
                        "Failed to store accommodation in database: %s", str(e)
                    )

                # Add to memory entities list
                observations = [
                    f"Located in {listing.location_info}",
                    f"Property type: {listing.property_type}",
                    f"Price: {listing.price_string}",
                ]

                if listing.rating:
                    observations.append(f"Rating: {listing.rating}/5")

                if listing.beds:
                    observations.append(f"Beds: {listing.beds}")

                if listing.bedrooms:
                    observations.append(f"Bedrooms: {listing.bedrooms}")

                if listing.bathrooms:
                    observations.append(f"Bathrooms: {listing.bathrooms}")

                memory_entities.append(
                    {
                        "name": f"Accommodation:{listing.id}",
                        "entityType": "Accommodation",
                        "observations": observations,
                        "destination": location,
                        "type": "airbnb",
                        "url": listing.url,
                    }
                )

            # Store entities in memory knowledge graph
            if memory_entities:
                try:
                    await memory_client.create_entities(memory_entities)
                    logger.info(
                        "Stored %s accommodations in memory graph", len(memory_entities)
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to store accommodations in memory: %s", str(e)
                    )

        except Exception as e:
            logger.warning("Error storing search results: %s", str(e))

    async def _store_listing_details(
        self,
        listing_details: AirbnbListingDetails,
        checkin: Optional[Union[str, date]] = None,
        checkout: Optional[Union[str, date]] = None,
    ) -> None:
        """Store detailed listing information in database and knowledge graph.

        Args:
            listing_details: Detailed listing information
            checkin: Check-in date
            checkout: Check-out date
        """
        try:
            # Store in Supabase
            db_client = get_db_client()
            accommodation_repo: AccommodationRepository = db_client.accommodations

            # Create detailed database record
            accommodation_data = {
                "external_id": listing_details.id,
                "name": listing_details.name,
                "type": "airbnb",
                "location": listing_details.location,
                "price": listing_details.price_total or listing_details.price_per_night,
                "status": "available",
                "metadata": listing_details.model_dump(
                    exclude={"id", "name", "location"}
                ),
            }

            if checkin:
                accommodation_data["check_in_date"] = (
                    checkin.isoformat() if isinstance(checkin, date) else checkin
                )
            if checkout:
                accommodation_data["check_out_date"] = (
                    checkout.isoformat() if isinstance(checkout, date) else checkout
                )

            # Store in Supabase asynchronously
            try:
                await accommodation_repo.create_or_update(accommodation_data)
            except Exception as e:
                logger.warning(
                    "Failed to store detailed accommodation in database: %s", str(e)
                )

            # Store in memory knowledge graph
            location_parts = listing_details.location.split(",")
            destination = location_parts[0].strip()

            # Create detailed observations
            observations = [
                f"Located in {listing_details.location}",
                f"Property type: {listing_details.property_type}",
            ]

            if listing_details.price_per_night:
                observations.append(
                    f"Price per night: {listing_details.price_per_night} "
                    f"{listing_details.currency}"
                )

            if listing_details.bedrooms:
                observations.append(f"Bedrooms: {listing_details.bedrooms}")

            if listing_details.beds:
                observations.append(f"Beds: {listing_details.beds}")

            if listing_details.bathrooms:
                observations.append(f"Bathrooms: {listing_details.bathrooms}")

            if listing_details.rating:
                observations.append(
                    f"Rating: {listing_details.rating}/5 with "
                    f'"{listing_details.reviews_count}" reviews'
                )

            if listing_details.amenities:
                amenities_text = ", ".join(listing_details.amenities[:10])
                observations.append(f"Amenities: {amenities_text}")

            if listing_details.host and listing_details.host.superhost:
                observations.append(
                    f"Hosted by {listing_details.host.name} (Superhost)"
                )
            elif listing_details.host:
                observations.append(f"Hosted by {listing_details.host.name}")

            # Add description as a separate observation
            if listing_details.description:
                # Truncate to a reasonable length
                max_desc_length = 500
                description = listing_details.description
                if len(description) > max_desc_length:
                    description = description[:max_desc_length] + "..."
                observations.append(description)

            # Create entity
            entity = {
                "name": f"Accommodation:{listing_details.id}",
                "entityType": "Accommodation",
                "observations": observations,
                "destination": destination,
                "type": "airbnb",
                "url": listing_details.url,
            }

            try:
                await memory_client.create_entities([entity])

                # Create relationship with destination
                relation = {
                    "from": f"Accommodation:{listing_details.id}",
                    "relationType": "is_located_in",
                    "to": destination,
                }
                await memory_client.create_relations([relation])

                logger.info(
                    "Stored detailed accommodation in memory graph: %s",
                    listing_details.name,
                )
            except Exception as e:
                logger.warning(
                    "Failed to store detailed accommodation in memory: %s", str(e)
                )

        except Exception as e:
            logger.warning("Error storing detailed listing: %s", str(e))
