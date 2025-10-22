"""Destination API schema façade referencing the finalized service models."""

from tripsage_core.services.business.destination_service import (
    Destination,
    DestinationCategory,
    DestinationRecommendation,
    DestinationRecommendationRequest,
    DestinationSearchRequest,
    DestinationSearchResponse,
    SavedDestination,
    SavedDestinationRequest,
)


__all__ = [
    "Destination",
    "DestinationCategory",
    "DestinationRecommendation",
    "DestinationRecommendationRequest",
    "DestinationSearchRequest",
    "DestinationSearchResponse",
    "SavedDestination",
    "SavedDestinationRequest",
]
