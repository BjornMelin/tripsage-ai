"""SearchFacade for TripSage.

This module provides a unified search interface using the strategy pattern.
It consolidates destination, activity, and unified search operations into
a single facade with pluggable strategies.
"""

from abc import ABC, abstractmethod
from typing import Any

from tripsage.api.schemas.activities import (
    ActivityResponse,
    ActivitySearchRequest,
    ActivitySearchResponse,
)
from tripsage.api.schemas.destinations import (
    Destination,
    DestinationRecommendation,
    DestinationRecommendationRequest,
    DestinationSearchRequest,
    DestinationSearchResponse,
    SavedDestination,
    SavedDestinationRequest,
)
from tripsage.api.schemas.search import UnifiedSearchRequest, UnifiedSearchResponse
from tripsage_core.utils.error_handling_utils import tripsage_safe_execute
from tripsage_core.utils.logging_utils import get_logger


logger = get_logger(__name__)


class SearchStrategy(ABC):
    """Abstract base class for search strategies."""

    @abstractmethod
    async def search(self, request: Any) -> Any:
        """Execute search with the given request."""

    @abstractmethod
    def get_strategy_type(self) -> str:
        """Return the strategy type identifier."""


class DestinationSearchStrategy(SearchStrategy):
    """Strategy for destination searches."""

    def __init__(self, destination_service: Any):
        """Initialize the destination search strategy."""
        self.destination_service = destination_service

    async def search(
        self, request: DestinationSearchRequest
    ) -> DestinationSearchResponse:
        """Execute destination search."""
        return await self.destination_service.search_destinations(request)

    def get_strategy_type(self) -> str:
        """Return the strategy type identifier."""
        return "destination"


class ActivitySearchStrategy(SearchStrategy):
    """Strategy for activity searches."""

    def __init__(self, activity_service: Any):
        """Initialize the activity search strategy."""
        self.activity_service = activity_service

    async def search(self, request: ActivitySearchRequest) -> ActivitySearchResponse:
        """Execute activity search."""
        return await self.activity_service.search_activities(request)

    def get_strategy_type(self) -> str:
        """Return the strategy type identifier."""
        return "activity"


class UnifiedSearchStrategy(SearchStrategy):
    """Strategy for unified searches."""

    def __init__(self, unified_search_service: Any):
        """Initialize the unified search strategy."""
        self.unified_search_service = unified_search_service

    async def search(self, request: UnifiedSearchRequest) -> UnifiedSearchResponse:
        """Execute unified search."""
        return await self.unified_search_service.unified_search(request)

    def get_strategy_type(self) -> str:
        """Return the strategy type identifier."""
        return "unified"


class SearchFacade:
    """Facade for all search operations using strategy pattern."""

    def __init__(
        self,
        destination_service: Any = None,
        activity_service: Any = None,
        unified_search_service: Any = None,
    ):
        """Initialize search facade with available services.

        Args:
            destination_service: Destination service instance
            activity_service: Activity service instance
            unified_search_service: Unified search service instance
        """
        self.strategies: dict[str, SearchStrategy] = {}

        if destination_service:
            self.strategies["destination"] = DestinationSearchStrategy(
                destination_service
            )

        if activity_service:
            self.strategies["activity"] = ActivitySearchStrategy(activity_service)

        if unified_search_service:
            self.strategies["unified"] = UnifiedSearchStrategy(unified_search_service)

        logger.info(
            "SearchFacade initialized with strategies: %s", list(self.strategies.keys())
        )

    @tripsage_safe_execute()
    async def search_destinations(
        self, request: DestinationSearchRequest
    ) -> DestinationSearchResponse:
        """Search for destinations.

        Args:
            request: Destination search request

        Returns:
            Destination search response

        Raises:
            ValueError: If destination strategy not available
        """
        strategy = self.strategies.get("destination")
        if not strategy:
            raise ValueError("Destination search strategy not available")

        logger.info("Executing destination search")
        return await strategy.search(request)

    @tripsage_safe_execute()
    async def search_activities(
        self, request: ActivitySearchRequest
    ) -> ActivitySearchResponse:
        """Search for activities.

        Args:
            request: Activity search request

        Returns:
            Activity search response

        Raises:
            ValueError: If activity strategy not available
        """
        strategy = self.strategies.get("activity")
        if not strategy:
            raise ValueError("Activity search strategy not available")

        logger.info(
            "Executing activity search for destination: %s", request.destination
        )
        return await strategy.search(request)

    @tripsage_safe_execute()
    async def unified_search(
        self, request: UnifiedSearchRequest
    ) -> UnifiedSearchResponse:
        """Perform unified search across multiple resource types.

        Args:
            request: Unified search request

        Returns:
            Unified search response

        Raises:
            ValueError: If unified search strategy not available
        """
        strategy = self.strategies.get("unified")
        if not strategy:
            raise ValueError("Unified search strategy not available")

        logger.info("Executing unified search for query: %s", request.query)
        return await strategy.search(request)

    @tripsage_safe_execute()
    async def get_search_suggestions(self, query: str, limit: int = 10) -> list[str]:
        """Get search suggestions.

        Args:
            query: The search query
            limit: Maximum number of suggestions

        Returns:
            List of search suggestions

        Raises:
            ValueError: If unified search strategy not available
        """
        strategy = self.strategies.get("unified")
        if not strategy or not isinstance(strategy, UnifiedSearchStrategy):
            raise ValueError("Unified search strategy not available")

        logger.info("Getting search suggestions for query: %s", query)
        # The unified search service has this method
        return await strategy.unified_search_service.get_search_suggestions(
            query, limit
        )

    @tripsage_safe_execute()
    async def get_activity_details(self, activity_id: str) -> ActivityResponse | None:
        """Get detailed information about a specific activity.

        Args:
            activity_id: The activity ID

        Returns:
            Activity details or None

        Raises:
            ValueError: If activity strategy not available
        """
        strategy = self.strategies.get("activity")
        if not strategy or not isinstance(strategy, ActivitySearchStrategy):
            raise ValueError("Activity search strategy not available")

        logger.info("Getting activity details for: %s", activity_id)
        return await strategy.activity_service.get_activity_details(activity_id)

    @tripsage_safe_execute()
    async def save_destination(
        self, user_id: str, request: SavedDestinationRequest
    ) -> SavedDestination:
        """Save a destination for the user.

        Args:
            user_id: The user ID
            request: Save destination request

        Returns:
            Saved destination

        Raises:
            ValueError: If destination strategy not available
        """
        strategy = self.strategies.get("destination")
        if not strategy or not isinstance(strategy, DestinationSearchStrategy):
            raise ValueError("Destination search strategy not available")

        logger.info("Saving destination for user: %s", user_id)
        return await strategy.destination_service.save_destination(user_id, request)

    @tripsage_safe_execute()
    async def get_saved_destinations(self, user_id: str) -> list[SavedDestination]:
        """Get saved destinations for the user.

        Args:
            user_id: The user ID

        Returns:
            List of saved destinations

        Raises:
            ValueError: If destination strategy not available
        """
        strategy = self.strategies.get("destination")
        if not strategy or not isinstance(strategy, DestinationSearchStrategy):
            raise ValueError("Destination search strategy not available")

        logger.info("Getting saved destinations for user: %s", user_id)
        return await strategy.destination_service.get_saved_destinations(user_id)

    @tripsage_safe_execute()
    async def get_destination_recommendations(
        self, user_id: str, recommendation_request: DestinationRecommendationRequest
    ) -> list[DestinationRecommendation]:
        """Get destination recommendations for the user.

        Args:
            user_id: The user ID
            recommendation_request: Recommendation request

        Returns:
            List of destination recommendations

        Raises:
            ValueError: If destination strategy not available
        """
        strategy = self.strategies.get("destination")
        if not strategy or not isinstance(strategy, DestinationSearchStrategy):
            raise ValueError("Destination search strategy not available")

        logger.info("Getting destination recommendations for user: %s", user_id)
        return await strategy.destination_service.get_destination_recommendations(
            user_id, recommendation_request
        )

    @tripsage_safe_execute()
    async def get_destination_details(
        self,
        destination_id: str,
        include_weather: bool = True,
        include_pois: bool = True,
        include_advisory: bool = True,
    ) -> Destination | None:
        """Get destination details.

        Args:
            destination_id: The destination ID
            include_weather: Whether to include weather
            include_pois: Whether to include POIs
            include_advisory: Whether to include advisory

        Returns:
            Destination details or None

        Raises:
            ValueError: If destination strategy not available
        """
        strategy = self.strategies.get("destination")
        if not strategy or not isinstance(strategy, DestinationSearchStrategy):
            raise ValueError("Destination search strategy not available")

        logger.info("Getting destination details for: %s", destination_id)
        return await strategy.destination_service.get_destination_details(
            destination_id, include_weather, include_pois, include_advisory
        )

    def get_available_strategies(self) -> list[str]:
        """Get list of available search strategies."""
        return list(self.strategies.keys())

    def has_strategy(self, strategy_type: str) -> bool:
        """Check if a specific strategy is available."""
        return strategy_type in self.strategies


# Dependency injection function
async def get_search_facade() -> SearchFacade:
    """Get search facade instance for dependency injection.

    Returns:
        SearchFacade instance
    """
    # Import here to avoid circular imports
    from tripsage_core.services.business.destination_service import DestinationService
    from tripsage_core.services.business.unified_search_service import (
        UnifiedSearchService,
    )

    # Initialize services (this would typically be done in a DI container)
    destination_service = DestinationService()
    activity_service = None  # Would need proper initialization with Google Maps service
    unified_search_service = UnifiedSearchService(
        destination_service=destination_service,
        activity_service=activity_service,
        cache_service=None,  # Would need proper cache service initialization
    )

    # Return the search facade instance
    return SearchFacade(
        destination_service=destination_service,
        activity_service=activity_service,
        unified_search_service=unified_search_service,
    )
